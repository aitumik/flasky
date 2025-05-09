from flask import render_template, session, redirect, url_for, abort, flash, request, make_response
from flask_login import login_required
from . import main
from flask_login import current_user
from flask import current_app
from .forms import NameForm, EditProfileForm, PostForm, CommentForm
from ..import db
from ..models import User, Permission, Post, Comment,User
from ..decorators import admin_required, permission_required
from ..email import send_email


@main.route("/", methods=['GET', 'POST'])
def home():
    form = PostForm()
    if form.validate_on_submit() and current_user.can(Permission.WRITE):
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        return redirect(url_for(".home"))

    # adding the pagination here
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['BLOGGING_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    users = User.query.all()[:5]
    return render_template('index.html', form=form, posts=posts, \
            pagination=pagination,users=users)

@main.route("/all")
@login_required
def show_all():
    resp = make_response(redirect(url_for('main.home')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp


@main.route("/followed")
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.home')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp


@main.route("/post/<int:id>",methods=['GET','POST'])
def post(id):
    form = CommentForm()
    post = Post.query.get_or_404(id)
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        # todo : send email to the owner of the post that they have received 
        #        a comment, the template will have the post and the comment
        #        
        send_email(post.author.email,"You have a new comment","auth/email/comment",comment=comment,post=post,user=post.author)
        flash("Your comment has been submitted")
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) / \
            current_app.config['BLOGGING_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=10,
        error_out=False)
    comments = pagination.items
    return render_template("post.html", posts=[post], form=form, comments=comments, pagination=pagination)


@main.route("/edit/<int:id>", methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash("The post has been updated")
        return redirect(url_for('main.post', id=post.id))
    form.body.data = post.body
    return render_template("edit_post.html", form=form)


@main.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash("Your profile has been updated")
        return redirect(url_for("main.user", username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", form=form)


# Admin edit form
@main.route("/edit-profile/<int:id>", methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.useraname.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash("The profile has been updated")
        return redirect(url_for('main.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template("edit_profile.html", form=form, user=user)


@main.route("/user/<username>")
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("The username does not exist")
        abort(404)
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template("user.html", user=user, posts=posts)


@main.route("/follow/<username>")
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Inavalid user")
        return redirect(url_for("main.home"))
    if current_user.is_following(user):
        flash("You are already following this user")
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash("You are now following {}".format(username))
    return redirect(url_for("main.user", username=username))


@main.route("/followers/<username>")
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user")
        return redirect(url_for("main.home"))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=10, error_out=False)
    follows = [{"user": item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of", endpoint='.followers', pagination=pagination, follows=follows)


@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.home'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=10,
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.home'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))


@main.route("/moderate")
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(page, per_page=4,error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments)

@main.route("/moderate/enable/<int:id>")
@login_required
@permission_required(Permission.MODERATE)
#def moderate_enable(id):
def moderator():
    #jcomment = Comment.query.get_or_404(id)
    #comment.disabled = False
    #db.session.add(comment)
    #return redirect(url_for('.moderate_disable',page=request.args.get('page', 1, type=int)))
    return "You have disable"

@main.route("/moderate/disable/<int:id>")
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('main.moderator'))


@main.route("/admin")
@login_required
@admin_required
def for_admins_only():
    return "For administrators"
