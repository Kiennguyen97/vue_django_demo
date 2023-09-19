from products.meili_search import client


def execute():
    """Main Function"""
    try:
        client.get_index("products")
    except Exception as e:
        client.create_index()

    try:
        client.reindex_all()
    except Exception as e:
        print(str(e))
