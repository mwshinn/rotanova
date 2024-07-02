#python3 -m flask --app controller run --host=0.0.0.0 --port=80
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
waitress-serve --host rota.cortexlab.net --port 8080 controller:app
