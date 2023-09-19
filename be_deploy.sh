docker-compose down
docker-compose up -d

docker-compose run --rm web python3 manage.py makemigrations --merge
docker-compose run --rm web python3 manage.py makemigrations products customers cms blog
docker-compose run --rm web python3 manage.py migrate

#docker-compose run --rm web python3 manage.py shell -c "from customers.models import CustomUser as User; User.objects.create_superuser('admin', password='admin123')"
