from products.models import Category, Product, ProductOption, Option, ProductOptionRel, Resource, ProductResource
from django.utils import timezone

#%%
import json
import pprint
import re

pp = pprint.PrettyPrinter().pprint

with open('./temp/data/bc_product_dump.json', 'r') as f:
    data = json.load(f)

with open(f"./temp/data/final_pricing.json", "r") as fp:
    pricedata = json.load(fp)

price_lookup = {}
for k in pricedata:
    i = list(k.values())[0]
    # price_lookup[i['original'][1]] = i['prices']['rrp']
    if 'Liberty' in i['original'][2]:
        price_lookup[list(i['help'][0].values())[0]] = i['prices']['rrp']
    else:
        price_lookup[i['original'][1]] = i['prices']['rrp']


    # if i['result'] == 'direct':
    #     price_lookup[i['original'][1]] = i['prices']['rrp']
    # else:
    #     part = i['help'][-1]
    #     if type(part) == list:
    #         part = part[-1]
    #     price_lookup[list(part.values())[0]] = i['prices']['rrp']

problems = []

#%%

grouped_options = {}
grouped_index = {}
count = 1

def break_sku(sku):
    try:
        if breakable := re.search('(R?\d{,6}(?:R(?!N)|L|^NR)?)([A-Z]{2})([AB](?!VIA){1}[A-Z]{2}|[AB](?=VIA|-){1})?(.{2,})?', sku):
            a, b, c, d = breakable.groups()
            if not a:
                return sku, '', '', ''
            if d == 'L' or d == 'R':
                a = a+d
                d = ''
            # print(f"{sku} -> {a}  {b} {c} {d}") # LR at end...
            return a, b, c, d
    except:
        return sku, '', '', ''
    return sku, '', '', ''


none_translate = {
'Basin / Slab Top|Clasico Vitreous China': 'VC',
 'Basin / Slab Top|Himalaya Quartz Slab Top (+ $277.00)': 'HY',
 'Basin / Slab Top|Midnight Stone Quartz Slab Top (+ $277.00)': 'MS',
 'Basin / Slab Top|Ponti Stonecast': 'PO',
 'Basin / Slab Top|Stonecast Slab Top (+ $277.00)': 'SC',
 'Basin / Slab Top|Via Matte White (+ $128.00)': 'VIAMW',
 'Basin / Slab Top|Via Stonecast': 'VIA',
 'Basin|Clasico Vitreous China': 'VC',
 'Basin|Ponti Stonecast': 'PO',
 'Basin|Stonecast (Interchangeable Tap)': 'SC',
 'Basin|Vercelli Vitreous China (+ $128.00)': 'VE',
 'Basin|Via Matte White': 'VIAMW',
 'Basin|Via Stonecast': 'VIA',
 'Basin|Vitreous China (Left Hand Tap)': 'LTH',
 'Basin|Vitreous China (Right Hand Tap)': 'RTH',
 'Rail|Toilet Roll Holder — Chrome': 'CH',
 'Rail|Towel Rail — Chrome': 'CH',
 'Slab Top|Himalaya Quartz Top': 'HY',
 'Slab Top|Midnight Stone Quartz Top': 'MS',
 'Slab Top|Stonecast': 'SC'
 }

def group_options(page):
    grouped_index[page['slug']] = []
    global count
    # if not group_name in grouped_options:
        # grouped_options[group_name] = {}
    prelim = {}
    # base_price = float(page['price'])
    for section in page['products']:
        # section_price = float(section['price'])
        # price_add = section_price - base_price if base_price <= section_price else base_price
        size_sku, colour_sku, rail_sku, top_sku = break_sku(section['sku'])
        for opt_dict in section['options']:
            _type = opt_dict['type']
            _value = opt_dict['value']
            _sku = size_sku
            if _type == 'Colour':
                _sku = colour_sku
            if _type == 'Basin' or _type == 'Slab Top' or _type == 'Basin / Slab Top':
                _sku = top_sku
            if _type == 'Rail':
                _sku = rail_sku
            if not _type in prelim:
                prelim[_type] = set()
            if _sku == None:
                none_lookup = f"{_type}|{_value}"
                _sku = none_translate[none_lookup]
                # none_set.add()
            # else:
            prelim[_type].add(f"{_value}|{_sku}")
        for _type, values in page.get('global_options').items():
            if not _type in prelim:
                prelim[_type] = set()
            for val in values:
                prelim[_type].add(f"{val['value']}|{val['value_sku']}")


    # pp(prelim)
    # print('*'*88)
    for _type, prelim_set in prelim.items():
        if prelim_set not in [set(i) for i in list(grouped_options.values())]:

            # print(prelim_set, [set(i) for i in list(grouped_options.values())])
            if _type == 'Size' or 'Demister' in _type:
                _type = f"{_type}: {page['slug']}"
            if _type in grouped_options:
                _type = f"{_type}_{count}"
                count+=1
            grouped_options[f"{_type}"] = prelim_set
        key = list(grouped_options.keys())[list(grouped_options.values()).index(prelim_set)]
        grouped_index[page['slug']].append(key)


# test = [i for i in parsed if 'brookfield' in i['slug']]

for page in data:
    group_options(page)


#%%

# testing
# data = [i for i in data if 'citi' in i['slug']]

opts = [
    "COLOUR",
    "SIZE",
    "SLAB_TOP",
    "BASIN",
    "EXTRUSION",
    "TAP_HOLE",
    "COSMETIC_DRAWER",
    "HANDLES",
    "OTHER"
]

for group, vals in grouped_options.items():
    _type = 'OTHER'
    for i in opts:
        if i.lower().replace('_', ' ') in group.lower():
            _type = i
    po, is_new = ProductOption.objects.get_or_create(
            option_type = _type
            , option_name = group
        )
    po.save()
    for val in vals:
        name, sku_add = val.split('|')

        o, is_new = Option.objects.get_or_create(
            productoption = po
            , name = name
            , sku_addition = sku_add
        )
        if _type == 'SIZE':
            full_price = price_lookup.get(sku_add)
            if not full_price:
                o.delete()
                continue
            o.price_adjust = full_price
        if _type == 'HANDLES':
            if sku_add in ['M', 'J', 'ROMA-C']:
                o.price_adjust = 49
            if sku_add in ['ROMA-NK', 'ROMA-B']:
                o.price_adjust = 67
            if sku_add in ['ROMA-GM']:
                o.price_adjust = 88

        if _type == 'COSMETIC_DRAWER':
            if sku_add in ['COSL', 'COSR']:
                o.price_adjust = 266
            if sku_add in ['COSLR']:
                o.price_adjust = 266 * 2


        if _type == 'BASIN':
            if sku_add in ['VE', 'VIAMW']:
                o.price_adjust = 132
            if sku_add in ['MS', 'SC', 'SCMW', 'HY']:
                o.price_adjust = 285

        if _type == 'EXTRUSION':
            o.price_adjust = 78

        o.save()

o, is_new = Option.objects.get_or_create(
    productoption = ProductOption.objects.get(option_type='EXTRUSION')
    , name = 'Brushed Nickel'
    , sku_addition = 'V1100NK'
)

o.save()


for page in data:
    try:
        if len(page['category']) == 2:
            parent_cat, sub_cat = page['category']
        else:
            sub_cat = page['category'][0]

        print(sub_cat.lower().replace(' ','-'))
        if sub_cat == 'Wall Hung Vanities':
            if not (sc := Category.objects.filter(name=sub_cat)):
                parent = Category.objects.get(slug='vanities-by-type')
                sc = Category.objects.create(name = sub_cat, parent_category = parent)
        if sub_cat == 'Mirrors':
            sc, is_new = Category.objects.get_or_create(slug='mirror')
        else:
            sc, is_new = Category.objects.get_or_create(name=sub_cat)



        product_page, is_new = Product.objects.get_or_create(
            slug = page['slug']
            , sku = page['slug']
            , list_price = price_lookup.get(page['sku'], 0)
        )

        product_page.name = page['page_name']
        product_page.description_long = page['description']
        product_page.category = sc
        product_page.description_short = page['page_name']

        product_page.save()


        for po in product_page.options.filter(option_type='SIZE'):
            for opt in po.option_set.all():
                if float(opt.price_adjust) >= float(product_page.list_price):
                    opt.price_adjust = float(opt.price_adjust) - float(product_page.list_price)
                    opt.save()
            po.save()
        product_page.save()

        for opt in grouped_index.get(page['slug'], []):
            po = ProductOption.objects.get(option_name=opt)
            default = po.option_set.order_by("price_adjust", "sku_addition").first()
            por, is_new = ProductOptionRel.objects.get_or_create(
                product = product_page
                , productoption = po
                , default_option = default
            )
            por.save()
            # po.product.add(product_page)
            # po.save()

        product_page.save()






    except Exception as e:
        problems.append({
            'page': page['slug']
            , 'exception': e
            # , 'optvalues': list(optvalues)
        })
        # break

pp(problems)
pp(len(problems))


# c = Category.objects.create(
#     name = 'Test Cates'
#     , slug = 'this-is-slug'
#     # , description = 'slug cat'
# )

# c.save()