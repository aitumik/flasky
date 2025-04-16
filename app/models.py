from app.exceptions import ValidationError
from flask import url_for
from app import db
import hashlib
import bleach
from markdown import markdown
from flask import request
from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from . import login_manager


class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


@login_manager.user_loader
def load_user(user_id):
    """
    This function loads the user from the database given and id
    user_id must be of type integer
    It is a call back function
    Example:
    user = load_user(1)
    """
    return User.query.get(int(user_id))

class Follow(db.Model):

    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer,db.ForeignKey('users.id'),primary_key = True)
    followed_id = db.Column(db.Integer,db.ForeignKey('users.id'),primary_key = True)
    timestamp = db.Column(db.DateTime,default = datetime.utcnow)


class Role(db.Model):
    """
    This table is used for storing roles in the db
    There are several roles
    """
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)

    #users with the this role
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self,**kwargs):
        super(Role,self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def add_permission(self,perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def reset_permissions(self):
        self.permissions = 0

    def remove_permission(self,perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def has_permission(self,perm):
        return self.permissions & int(perm) == int(perm)



    @staticmethod
    def insert_roles():

        roles = {
            'User': [Permission.FOLLOW,Permission.COMMENT,Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT,Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT,Permission.WRITE, Permission.MODERATE,Permission.ADMIN],
        }

        default_role = "User"
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()



    def __repr__(self):
        """
        Readable representation of roles
        """
        return "<Role %r>" % self.name


class User(UserMixin, db.Model):
    """
    This table is used to store the users and their details like emails
    and password
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    confirmed = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(),default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(),default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship('Post',backref='author',lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    #followers and followed

    followed = db.relationship('Follow',
        foreign_keys = [Follow.follower_id],
        backref=db.backref('follower', lazy='joined'),
        lazy='dynamic',
        cascade='all, delete-orphan')

    followers = db.relationship('Follow',
        foreign_keys=[Follow.followed_id],
        backref=db.backref('followed', lazy='joined'),
        lazy='dynamic',
        cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if str(self.email) == str(current_app.config['BLOGGING_ADMIN']):
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        #follow himuselfu
        #self.follow(self)

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        from faker import Faker

        seed()
        f = Faker()
        for i in range(count):
            profile = f.simple_profile()
            u = User(email=profile['mail'],
                    username=profile['username'],
                    password=f.password(),
                    confirmed=True,
                    name=profile['name'],
                    location=profile['address'],
                    about_me = f.text(),
                    member_since = f.past_date())
            db.session.add(u)

            try:
                db.session.commit()
            except Exception as e:
                print(e)
                db.session.rollback()
    @property
    def password(self):
        raise AttributeError("Password is not readable")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({"confirm": self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def follow(self,user):
        if not self.is_following(user):
            f = Follow(follower=self,followed=user)
            db.session.add(f)

    def unfollow(self,user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self,user):
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self,user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def generate_auth_token(self,expiration):
        s = Serializer(current_app.config['SECRET_KEY'],expires_in=expiration)
        return s.dumps({"id":self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def to_json(self):
        json_user = {
                "url":url_for('api.get_user',id=self.id),
                "username":self.username,
                "member_since":self.member_since,
                "last_seen":self.last_seen,
                "posts_url":url_for('api.get_user_posts',id=self.id),
                "followed_posts_url":url_for('api.get_user_followed_posts',id=self.id),
                "post_count":self.posts.count()
        }
        return json_user

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar(self,size=100,default='identicon',rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://secure.gravatar.com/avatar'

        hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return "{url}/{hash}?s={size}&d={default}&r={rating}".format(url=url,hash=hash,size=size,default=default,rating=rating)

    def generate_email_change_token(self,new_email,expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'],expiration)
        return s.dumps(
                {"change_email": self.id,"new_email": new_email}).decode("utf-8")

    def change_email(self,token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.decode("utf-8"))
        except:
            return False
        if data.get("new_email") != self.id:
            return False
        new_email = data.get("new_email")
        if self.query.filter_by(email=new_email).first() is not None:
            return False 
        self.email = new_email
        self.avatar_hash = self.gravatar()
        db.session.add(self)
        db.session.commit()


    def __repr__(self):
        return "<User %r>" % self.username

class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

class Post(db.Model):

    __tablename__ = 'posts'

    id = db.Column(db.Integer,primary_key = True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime,index=True,default = datetime.utcnow)
    author_id = db.Column(db.Integer,db.ForeignKey("users.id"))
    comments = db.relationship('Comment',backref='post',lazy='dynamic')

    def to_json(self):
        json_post = {
                "url":url_for("api.get_post",id=self.id),
                "body":self.body,
                "body_html":self.body_html,
                "timestamp":self.timestamp,
                "author_url":url_for('api.get_user',id=self.author.id),
                'comments_url': url_for('api.get_post_comments', id=self.id),
                "comment_count":self.comments.count()
            }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == "":
            raise ValidationError("post does not have a body")
        return Post(body=body)

    @staticmethod
    def on_changed_body(target,value,oldvalue,initiator):
        allowed_tags = ['a','abbr', 'acronym', 'b', 'blockquote', 'code',
'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(markdown(value,output_format="html"),tags=allowed_tags,strip=True))



    @staticmethod
    def generate_fake(count=100):
        from random import seed,randint
        import faker

        seed()
        user_count = User.query.count()
        for i in range(count):
            f = faker.Faker()
            u = User.query.offset(randint(0,user_count -1)).first()
            p = Post(body = f.text(),
                    timestamp=f.date_time(),
                    author=u)
            db.session.add(p)
            db.session.commit()

db.event.listen(Post.body,'set',Post.on_changed_body)


class Like(db.Model):

    __tablename__ = "likes"

    id = db.Column(db.Integer,primary_key=True)
    post_id = db.Column(db.Integer,db.ForeignKey('posts.id'))
    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))

    @staticmethod
    def on_changed_body(target,value,oldvalue,initiator):
        pass 


class Comment(db.Model):

    __tablename__ = "comments"

    id = db.Column(db.Integer,primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer,db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target,value,oldvalue,initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i','strong']
        target.body_html = bleach.linkify(bleach.clean(markdown(value,output_format='html'),tags=allowed_tags,strip=True))

db.event.listen(Comment.body,'set',Comment.on_changed_body)
login_manager.anonymous_user = AnonymousUser
