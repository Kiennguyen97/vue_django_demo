import re
import time

import meilisearch

from django.conf import settings
from odoo.utils import bulk_create
from products.models import Product
import re


class SearchClient:
    def __init__(self):
        self.index_name = settings.MEILI_INDEDX
        self.client = meilisearch.Client(settings.MEILISEARCH_URL, settings.MEILI_MASTER_KEY)
        self.index = self.client.index(self.index_name)

    def get_index(self, uid: str):
        return self.client.get_index(uid)

    def create_index(self):
        self.client.create_index(self.index_name, {"primaryKey": "sku"})
        self.client.index(self.index_name).update_settings(
            {
                # controls how the results are ordered
                "rankingRules": [
                    "words",
                    "typo",
                    "attribute",
                    "ordering:desc",
                    "proximity",
                    "sort",
                    "exactness",
                ],
                # controls the attributes searched on and
                # the weighting of each
                "searchableAttributes": [
                    "code",
                    "sku_lookup",
                    "name",
                    "list_price",
                    "is_featured",
                    "is_free_shipping",
                    "meta_keywords",
                    "description_long",
                    "sku_addition",
                ],
                "filterableAttributes": [
                    "code",
                    "list_price",
                    "is_featured",
                    "is_free_shipping",
                    "sku_lookup",
                    "sku_addition",
                ],
                "sortableAttributes": [
                    "ordering",
                    "list_price",
                    "name"
                ]
            }
        )

    def reindex_all(self):
        documents = self.load_documents([])

        result = self.index.add_documents(documents)
        task_uid = result["taskUid"]

        time.sleep(5)
        start = time.time()
        task = self.index.get_task(task_uid)
        while task["status"] not in ("succeeded", "failed"):
            time.sleep(5)
            if time.time() - start > 540:
                print("timeout")
                raise
        if task["status"] == "failed":
            print(task)
            print("failed")
            raise

    def reindex_add_by_ids(self, ids: []):
        if len(ids):
            documents = self.load_documents(ids)
            result = self.index.add_documents(documents)
            task_uid = result["taskUid"]

            time.sleep(5)
            start = time.time()
            task = self.index.get_task(task_uid)
            while task["status"] not in ("succeeded", "failed"):
                time.sleep(5)
                if time.time() - start > 120:
                    print("timeout")
                    raise
            if task["status"] == "failed":
                print(task)
                print("failed")
                raise

    def reindex_up_by_ids(self, ids: []):
        if len(ids):
            documents = self.load_documents(ids)
            result = self.index.update_documents(documents)
            task_uid = result["taskUid"]

            time.sleep(5)
            start = time.time()
            task = self.index.get_task(task_uid)
            while task["status"] not in ("succeeded", "failed"):
                time.sleep(5)
                if time.time() - start > 120:
                    print("timeout")
                    raise
            if task["status"] == "failed":
                print(task)
                print("failed")
                raise

    def load_documents(self, ids: []):
        cleanse_str = lambda x: re.sub(r"[\W_]+", "", x)
        # we need to have a string without any special chars
        # that serves as the index key ('sku')
        # we put the original sku (with special chars) into sku_lookup
        if len(ids):
            products = Product.objects.filter(sku__in=ids).all()
        else:
            products = Product.objects.all()
        prod_list = []
        for product in products:
            if len(cleanse_str(product.sku)) > 0:
                prod_list.append(
                    {
                        "sku": cleanse_str(product.sku),
                        "slug": product.get_absolute_url(),
                        "name": product.name,
                        "code": cleanse_str(product.get_product_sku()),
                        "description_long": product.description_long,
                        "meta_keywords": product.meta_keywords,
                        "list_price": float(product.list_price),
                        "max_price": float(product.get_max_price()),
                        "ordering": int(product.ordering),
                        "sku_lookup": product.sku,
                        "sku_addition": product.get_sku_additions,
                        "image": product.get_image_hi_res_urls()[0],
                        "is_featured": 1 if product.is_featured else 2,
                        "is_free_shipping": 1 if product.is_featured else 2,
                    }
                )
        print(f"adding docs of len {len(prod_list)}")
        return prod_list

    def create_query(self, query, limit=10000, filters=[]):
        sku_additions = query.split()
        list_search = []
        if len(sku_additions) == 1:
            sku_addition = sku_additions[0]
            match = re.search(r'\d+', sku_addition)
            if match:
                sku_pre = sku_addition[:match.start()]
                sku = sku_pre + match.group()
                sku_addition = sku_addition[match.end():]
                # get length of sku_addition
                sku_addition_len = len(sku_addition)
                number_loop = sku_addition_len+1 if sku_addition_len < 3 else 3
                for i in range(number_loop):
                    list_sku_additions = [sku_addition[i:]] if sku_addition[i:] else []
                    list_sku_additions.append(f"{sku+sku_addition[:i]}")
                    sku_addition_filters = [" AND ".join([f"sku_addition IN ['{x}']" for x in list_sku_additions])]
                    sku_addition_filters.extend(filters)
                    list_search.append({
                        "query": f"{sku+sku_addition[:i]}",
                        "filters": sku_addition_filters
                    })
        else:
            sku_additions.append(query)
            sku_addition_filters = [" AND ".join([f"sku_addition IN ['{x}']" for x in sku_additions])]
            sku_addition_filters.extend(filters)
            list_search.append({
                "query": query,
                "filters": sku_addition_filters
            })
        res = {'totalHits': 0}
        if len(list_search):
            query_search = '*'
            filters_search = [' OR '.join([f"({x['filters'][0]})" for x in list_search])]
            res = self.index.search(
                query_search,
                {
                    "attributesToRetrieve": ["code", "sku_lookup", "name"],
                    "filter": filters_search,
                    "hitsPerPage": limit,
                    "page": 1,
                },
            )

        if res['totalHits'] == 0:
            res = self.index.search(
                query,
                {
                    "attributesToRetrieve": ["code", "sku_lookup", "name"],
                    "filter": filters,
                    "hitsPerPage": limit,
                    "page": 1,
                },
            )

        skus = []
        # prod_ordering = []
        # totalHits = int(res["totalHits"])
        for x in res["hits"]:
            if x.get("sku_lookup"):
                # prod_ordering.append(tuple([x["sku_lookup"], totalHits]))
                skus.append(x["sku_lookup"])
                # totalHits -= 1

        # return skus, prod_ordering
        return skus

    def delete_item():
        # self.index.delete_document()
        pass

    def delete_all_items(self):
        self.index.delete_all_documents()

    def update_item():
        pass


client = SearchClient()
