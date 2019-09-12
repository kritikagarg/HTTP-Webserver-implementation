#./run.sh

sudo docker build --tag=echoapp .
sudo docker run -p 80:80 echoapp
