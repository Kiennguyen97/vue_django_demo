docker-compose down
docker-compose up -d
docker-compose up -d db

docker exec -i vue_db psql -U admin -d website < db.sql

# if error: "psql: FATAL:  database "website" does not exist"
