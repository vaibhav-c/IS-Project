from apps.home import blueprint
from flask import render_template, request
from flask_login import login_required, current_user
from jinja2 import TemplateNotFound
import hashlib
import cv2
import numpy
from PIL import Image
import random
import string
import os
import sqlite3

def storeInImageTable(name, person, sender):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    cur.execute('create table if not exists Image (sender text, receiver text, name text);')
    cur.execute('insert into Image values ("' + sender + '", "' + person + '", "' + name + '");')
    conn.commit()
    conn.close()

def storeInHashTable(comment, hashed):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    cur.execute('create table if not exists Hash (comment text, hashed text);')
    cur.execute('insert into Hash values ("' + comment + '", "' + hashed + '");')
    conn.commit()
    conn.close()

def getFromImageTable(user):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    cur.execute('select name from Image where receiver = "' + user + '";')
    desc = cur.description
    column_names = [col[0] for col in desc] 
    data = [dict(zip(column_names, row)) for row in cur.fetchall()]
    conn.close()
    return data

def getFromHashTable(hashcode):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    hashcode = hashcode.split('\x00')[-1]
    cur.execute('select comment from Hash where hashed = "' + hashcode +'";')
    desc = cur.description
    column_names = [col[0] for col in desc] 
    data = [dict(zip(column_names, row)) for row in cur.fetchall()]
    conn.close()
    return data

def putCodeInImage(img, hashed, name):
    result = ''.join(format(ord(i), '08b') for i in hashed)
    r = list(result)
    k = 0
    for i in range (0, numpy.shape(img)[0]):
        for j in range(0, numpy.shape(img)[1]):
            for l in range(0, numpy.shape(img)[2]):
                s = bin(img[i][j][l]).replace('0b', '')
                m = list(s)
                if k < len(r):
                    m[-1] = r[k]
                    s = ''.join(m)
                    img[i][j][l] = int(s)
                else:
                    break
                k += 1
            if k >= len(r):
                break
        if k >= len(r):
            break
    img = Image.fromarray(img.astype('uint8'))
    img.save('apps/static/uploads/' + name)

def getCodeFromImage(img):
    k = 0
    decode = []
    for i in range (0, numpy.shape(img)[0]):
        for j in range(0, numpy.shape(img)[1]):
            for l in range(0, numpy.shape(img)[2]):
                s = bin(img[i][j][l]).replace('0b', '')
                m = list(s)
                if k < 64 * 8:
                    decode.append(m[-1])
                else:
                    break
                k += 1
            if k >= 64 * 8:
                break
        if k >= 64 * 8:
            break
    bin_data = ''.join(decode)
    binary_int = int(bin_data, 2)
    byte_number = binary_int.bit_length() + 7 // 8
    binary_array = binary_int.to_bytes(byte_number, "big")
    ascii_text = binary_array.decode()
    return ascii_text

@blueprint.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if str(current_user) == 'admin':
        if(request.method == 'POST'):
            if 'inputfile' in request.files:
                img = cv2.imdecode(numpy.fromstring(request.files['inputfile'].read(), numpy.uint8), cv2.IMREAD_UNCHANGED)
                uploadf = request.files['inputfile']
                comment = request.form.get('comment')
                comment = str(comment).replace('"', "'")
                hashed = hashlib.sha256(comment.encode()).hexdigest()
                person = request.form.get('person')
                N = 7
                res = ''.join(random.choices(string.ascii_uppercase + string.digits, k = N))
                name =  str(res) + '.' + uploadf.filename.rsplit('.', 1)[1].lower()
                sender = 'admin'
                putCodeInImage(img, hashed, name)
                storeInImageTable(name, person, sender)
                storeInHashTable(comment, hashed)
        return render_template('home/admin.html', segment='index')
    else:
        if request.method == 'POST':
            uploadf = request.files['inputfile']
            person = request.form.get('person')
            N = 7
            res = ''.join(random.choices(string.ascii_uppercase + string.digits, k = N))
            name =  str(res) + '.' + uploadf.filename.rsplit('.', 1)[1].lower()
            sender = str(current_user)
            storeInImageTable(name, person, sender)
            if(uploadf):
                try:
                    uploadf.save(os.path.join('webinterface/apps/static/uploads/', name))
                except:
                    uploadf.save(os.path.join('apps/static/uploads/', name))
        names = getFromImageTable(str(current_user))
        allData = {
            'name': [],
            'code': []
        }
        l = []
        for i in range (0, len(names)):
            l.append(names[i]['name'])
        for i in l:
            p = 'apps/static/uploads/' + i
            img = Image.open(p, 'r')
            hashcode = getCodeFromImage(numpy.asarray(img))
            code = getFromHashTable(hashcode)
            allData['name'].append(i)
            try:
                allData['code'].append(code[0]['comment'])
            except:
                print('Normal Message')
        return render_template('home/index.html', segment='index', allData = allData)

@blueprint.route('/<template>')
@login_required
def route_template(template):

    try:

        if not template.endswith('.html'):
            pass

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        return render_template('home/page-500.html'), 500


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None
