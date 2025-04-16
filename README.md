# FlaskyBlog 

FlaskyBlog is a social blogging web application made with **Flask**. It allows users to **register**,**login** and more like **posting and liking**

## Author
Nathan Kimutai[(https://github.com/aitumik)]

## Installation
If you have a linux distro then you would setup this project by following the below instructions.

1. Clone the repository to your local machine
```sh
$ git clone https://github.com/aitumik/flasky
```

2. Change the working directory to the cloned application
```bash
cd flasky
```

3. Install all the requirements
```bash
pip3 install -r requirements.txt
```

Or with docker
```bash
sudo docker-compose up -d
```

## Export the environment variables
Export the following envrironment variables for confirmation emails to be sent
```bash
export MAIL_ADMIN=<YOUR ADMIN MAIL>
export MAIL_SENDER=<YOUR MAIL SENDER>
export MAIL_USERNAME=<YOUR MAIL USERNAME>
export MAIL_PASSWORD=<YOUR MAIL PASSWORD>
```
