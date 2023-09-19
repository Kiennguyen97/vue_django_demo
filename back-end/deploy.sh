docker-compose down
docker-compose up -d


#sudo rm -rf src/products/migrations
#sudo rm -rf src/customers/migrations
#sudo rm -rf src/cms/migrations
#sudo rm -rf src/blog/migrations


docker-compose run --rm web python3 manage.py makemigrations --merge
docker-compose run --rm web python3 manage.py makemigrations products customers cms blog
docker-compose run --rm web python3 manage.py migrate


#docker-compose run --rm web python3 manage.py collectstatic

#TODO: Back up DB
#docker-compose run --rm web python3 manage.py dumpdata products.Category --output=data/fixtures/categories.json
#docker-compose run --rm web python3 manage.py dumpdata products.Product --output=data/fixtures/products.json
#
#docker-compose run --rm web python3 manage.py dumpdata products.StoreLocation --output=data/fixtures/store_locations.json
#docker-compose run --rm web python3 manage.py dumpdata products.ProductResource --output=data/fixtures/product_resources.json
#docker-compose run --rm web python3 manage.py dumpdata products.ProductResourceRel --output=data/fixtures/product_resource_rels.json
#docker-compose run --rm web python3 manage.py dumpdata products.RelateProduct --output=data/fixtures/relate_products.json
#docker-compose run --rm web python3 manage.py dumpdata products.GalleryProduct --output=data/fixtures/gallery_product.json
#docker-compose run --rm web python3 manage.py dumpdata products.Resource --output=data/fixtures/resources.json
#docker-compose run --rm web python3 manage.py dumpdata products.Option --output=data/fixtures/options.json
#docker-compose run --rm web python3 manage.py dumpdata products.OptionDependRel --output=data/fixtures/option_depend_rels.json
#docker-compose run --rm web python3 manage.py dumpdata products.ProductOption --output=data/fixtures/product_options.json
#docker-compose run --rm web python3 manage.py dumpdata products.ProductOptionRel --output=data/fixtures/product_option_rels.json
#docker-compose run --rm web python3 manage.py dumpdata products.ProductOptionDependRel --output=data/fixtures/product_option_depend_rels.json
#docker-compose run --rm web python3 manage.py dumpdata products.NZRegion --output=data/fixtures/nz_region.json



# TODO: Import data
#psql -h localhost -p 5437 -U admin -d website < db.sql
#scp /home/kiennv@aht.local/NB_Projects/django/newtech-website-django/db.sql aht_g3@192.168.1.14:3022:/home/aht_g3/projects/newtech-website-django
#docker-compose down -v
#docker-compose up -d
#docker exec -i newtech-db-services psql -U admin -d website < db.sql


#cat src/data/fixtures/nz_region.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/store_locations.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/categories.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/products.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/products/fixtures/products.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#
#cat src/data/fixtures/options.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/resources.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/product_resources.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/product_resource_rels.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/relate_products.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/gallery_product.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/product_options.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/option_depend_rels.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/product_option_rels.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#cat src/data/fixtures/product_option_depend_rels.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -
#
##TODO: Other
#cat src/blog/fixtures/blogpost.json | docker exec -i newtech-web-services python3 manage.py loaddata --format=json -






#docker-compose run --rm web python3 manage.py shell -c "from customers.models import CustomUser as User; User.objects.create_superuser('admin', password='admin123')"




docker-compose run --rm web python3 manage.py meilisearch
#docker-compose run --rm web python3 manage.py update_product_code
#docker-compose run --rm web python3 manage.py update_categories