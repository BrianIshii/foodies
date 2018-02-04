import base64
import os
import sys

from flask import Flask, redirect, render_template, request

from google.cloud import datastore
from google.cloud import storage
from google.cloud import vision


app = Flask(__name__)


@app.route('/')
def homepage():
    # Create a Cloud Datastore client.
    datastore_client = datastore.Client("foodies-194120")

    # Use the Cloud Datastore client to fetch information from Datastore about
    # each photo.
    #query = datastore_client.query(kind='Photos')
    #image_entities = list(query.fetch())    

    # Return a Jinja2 HTML template.
    return render_template('homepage.html')

@app.route('/upload_photo', methods=['GET', 'POST'])
def upload_photo():

    # Create a Cloud Storage client.
    storage_client = storage.Client()

    # Get the Cloud Storage bucket that the file will be uploaded to.
    bucket = storage_client.get_bucket(os.environ.get('CLOUD_STORAGE_BUCKET'))


    kind = 'Photo' 
    # Create a new blob and upload the file's content to Cloud Storage.
    photo = request.files['file']
    blob = bucket.blob(photo.filename)
    blob.upload_from_string(
            photo.read(), content_type=photo.content_type)

    # Make the blob publicly viewable.
    blob.make_public()
    image_public_url = blob.public_url
    
    # Create a Cloud Vision client.
    vision_client = vision.ImageAnnotatorClient()

    # Retrieve a Vision API response for the photo stored in Cloud Storage
    source_uri = 'gs://{}/{}'.format(os.environ.get('CLOUD_STORAGE_BUCKET'), blob.name)
    response = vision_client.annotate_image({
        'image': {'source': {'image_uri': source_uri}},
    })
    labels = response.label_annotations
    web_entities = response.web_detection.web_entities

    # Create a Cloud Datastore client
    datastore_client = datastore.Client()

    # The name/ID for the new entity
    name = blob.name

    # Create the Cloud Datastore key for the new entity
    key = datastore_client.key(kind, name)

    # Construct the new entity using the key. Set dictionary values for entity
    # keys image_public_url and label. If we are using python version 2, we need to convert
    # our image URL to unicode to save it to Datastore properly.
    entity = datastore.Entity(key)
    if sys.version_info >= (3, 0):
        entity['image_public_url'] = image_public_url
    else:
        entity['image_public_url'] = unicode(image_public_url, "utf-8")
    entity['label'] = labels[0].description

    # Save the new entity to Datastore
    datastore_client.put(entity)

    # TODO: Get user information through a form 
    user_entity = create_user(username)

    labels = check_fruit(labels)
    # Redirect to the home page.
    ingredients = print_ingredients()
    return render_template('homepage.html', labels=labels, public_url=image_public_url, ingredients=ingredients)


@app.route('/get_username', methods=['GET', 'POST'])
def get_username():
    username = request.form['inputName']
    print(username)
    return render_template('homepage.html', name=username)

def create_user(username):
    datastore_client = datastore.Client()
    entity_kind = 'Person'
    key = datastore_client.key(entity_kind, username)
    entity = datastore.Entity(key)
    entity.update({
        'name':username,
        'ingredients':['apple']
        })
    return entity 

@app.errorhandler(500)
def server_error(e):
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500

@app.route('/showSignUp')
def showSignUp():
    return render_template('signup.html')

def check_fruit(labels, user):
    fruit_labels = []
    fruits = ["apple","apricot","avocado","banana","bell pepper",
        "bilberry","blackberry","blackcurrant","blood orange","blueberry",
        "boysenberry","breadfruit","canary melon","cantaloupe","cherimoya",
        "cherry","chili pepper","clementine","cloudberry","coconut","cranberry",
        "cucumber","currant","damson","date","dragonfruit","durian","eggplant",
        "elderberry","feijoa","fig","goji berry","gooseberry","grape",
        "grapefruit","guava","honeydew","huckleberry","jackfruit","jambul",
        "jujube","kiwi fruit","kumquat","lemon","lime","loquat","lychee",
        "mandarine","mango","mulberry","nectarine","nut","olive","orange",
        "pamelo","papaya","passionfruit","peach","pear","persimmon","physalis",
        "pineapple","plum","pomegranate","pomelo","purple mangosteen","quince","raisin",
        "rambutan","raspberry","redcurrant","rock melon","salal berry","satsuma",
        "star fruit","strawberry","tamarillo","tangerine","tomato","ugli fruit",
        "watermelon"]
    for label in labels:
        for fruit in fruits:
            if label.description == fruit:
                update_ingredients(user, label.description)
                print("new ingredient")
                print(label.description)
                fruit_labels.append(label)
    return fruit_labels

def update_ingredients(user, label):
    user.update({
        ingredients.append(label)})
    datastore_client.put(user)

"""
def check_ingredients(label):
    datastore_client = datastore.Client("foodies-194120")
    query = datastore_client.query(kind='Ingredient')
    ingredients = list(query.fetch())
    for i in ingredients:
        if (i.key.name == label.description):
            print("same")
            temp = datastore_client.get(i.key.name)
            temp['count'] = temp['count'] + 1
            datastore_client.put(temp)
            return True
    return False
"""

def print_ingredients():
    ingred_list = []
    datastore_client = datastore.Client("foodies-194120")
    query = datastore_client.query(kind='Person')
    user = list(query.fetch())[0]
    for i in user.key.ingredients:
        print(i)
        ingred_list.append(i)
    return ingred_list


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
