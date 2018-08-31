
# coding: utf-8

# In[14]:


import pickle
import copy
from copy import deepcopy
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("path_old")
parser.add_argument("path_new")
parser.add_argument("outfile")
args = parser.parse_args()

def get_data(src):
    with open(src, 'br') as f:
        data = pickle.load(f)
    return data

def is_double(cat_name, data):
    for dic in data:
        if dic['name'] == cat_name:
            return True
    return False

def get_annotations_by_category_id(category_id, data):
    return [ann for ann in data if ann['category_id'] == category_id]

def check_category_number(category_name, data):
    return [category['id'] for category in data if category['name'] == category_name]

def get_annotations_by_image_id(image_id, data):
    return [ann for ann in data['annotations'] if ann['image_id'] == image_id]

def append_per_category(image, category, data):
    category_annotations = []
    global n
    category_id = check_category_number(category['name'], data['categories'])
    if category_id:
        annotations = get_annotations_by_image_id(image['id'], data)
        old_annotations = get_annotations_by_category_id(category_id[0], annotations)
        if old_annotations:
            for annotation in old_annotations:
                a = copy.deepcopy(annotation)
                a['id'] = n
                a['category_id'] = category['id']
                category_annotations.append(a)
                n += 1
    return category_annotations

m = 0
def copy_categories(src):
    global m
    categories = []
    for category in src['categories']:
        cat = copy.deepcopy(category)
        if src == data_new:
            if not is_double(cat['name'], data_old['categories']):
                cat['id'] = m
                categories.append(cat)
                m += 1
        else:
            cat['id'] = m
            categories.append(cat)
            m += 1
    return categories
        
data_old = get_data(args.path_old)
data_new = get_data(args.path_new)

data_merged = {}
data_merged['info'] = data_old['info']
data_merged['images'] = data_old['images']

categories_merged = copy_categories(data_old) + copy_categories(data_new)

annotations_merged = []
old_annotations = []
new_annotations = [] 

for image in data_merged['images']:
    n = 0
    for category in categories_merged:
        old_annotations = append_per_category(image, category, data_old)
        new_annotations = append_per_category(image, category, data_new)

        for a in old_annotations:
            annotations_merged.append(a)
        for a in new_annotations:
            annotations_merged.append(a)

data_merged['categories'] = categories_merged
data_merged['annotations'] = annotations_merged
            
with open(args.outfile, 'bw') as f:
    pickle.dump(data_merged, f)


# In[76]:


# path_old = '/home/julia/razmetka/outdoor/amsterdam_dam/annotations_people.pickle'
# path_new = '/home/julia/razmetka/outdoor/amsterdam_dam/annotations_cars.pickle'
# outfile = '/home/julia/razmetka/outdoor/amsterdam_dam/annotations.pickle'

