# Created by Riku Miyao (@YAYtears)
# Modified by ZelKnow (@ZelKnow)

from backports import csv
from hearthstone.deckstrings import Deck
from hearthstone.deckstrings import FormatType
import json
# Python3 version https://pillow.readthedocs.io
from PIL import Image, ImageDraw, ImageFont
import io
import os
import argparse
import re
import requests
from html.parser import HTMLParser
import time

# https://github.com/HearthSim/hs-card-tiles
tile_loc = 'hs-card-tiles/Tiles/'

# generated from the the hearthstone client
tile_container_number = 'resources/tile_container_number.png'
tile_container_open = 'resources/tile_container_open.png'
star = 'resources/star.png'

number_font = 'resources/Belwe-Bold.ttf'

with open('config.json', encoding="utf-8") as json_file:
    cfg = json.load(json_file)
supported_locale = cfg.keys()

card_dict = {}
def initial_card_dict(locale):
    with open("resources/"+locale+"/cards.collectible.json", encoding="utf-8") as json_file:
        data = json.load(json_file)
        card_dict[locale] = {}
        for card in data:
            card_dict[locale][card['dbfId']] = card

def interpolate_color(minval, maxval, val, color_palette):
    """ Computes intermediate RGB color of a value in the range of minval-maxval
        based on color_palette representing the range. """
    #stack overflow is bae
    max_index = len(color_palette)-1
    v = float(val-minval) / float(maxval-minval) * max_index
    i1, i2 = int(v), min(int(v)+1, max_index)
    (r1, g1, b1, a1), (r2, g2, b2, a2) = color_palette[i1], color_palette[i2]
    f = v - i1
    return int(r1 + f*(r2-r1)), int(g1 + f*(g2-g1)), int(b1 + f*(b2-b1)), int(a1 + f*(a2-a1))

def draw_shadow(draw,x,y,text,font,shadowcolor="black"):
    # thin border
    draw.text((x-1, y-1), text, font=font, fill=shadowcolor)
    draw.text((x+1, y+1), text, font=font, fill=shadowcolor)
    draw.text((x+1, y-1), text, font=font, fill=shadowcolor)
    draw.text((x-1, y+1), text, font=font, fill=shadowcolor)

def find_code(text):
    line = text.strip()
    for x in line.split(' '):
        if x.startswith('AAE'):
            return x
    return line

def parse_deck(text):
    for i in range(3):
        try:
            deck = Deck.from_deckstring(text+'='*i)
            return deck
        except Exception as e:
            continue
    return None

def deck_to_image(deck, name, locale='enUS', handle=None):
    if locale not in card_dict:
        initial_card_dict(locale)
    if deck.heroes[0] not in card_dict[locale]:
        print(deck.as_deckstring)
    hero = card_dict[locale][deck.heroes[0]]
    imclass = Image.open('resources/{}.jpg'.format(hero['cardClass'].lower()))
    cards = [(card_dict[locale][x[0]],x[1]) for x in deck.cards]
    cards.sort(key = lambda x:(x[0]['cost'], x[0]['name']))
    width = 243
    if handle is None: 
        height = 39 * len(cards) + imclass.size[1]
    else:
        height = 39 * len(cards) + imclass.size[1] + 30
    
    master = Image.new('RGBA', (width, height))
    for index, (card, count) in enumerate(cards):
        image = '{}{}.png'.format(tile_loc, card['id'])
        im = Image.open(image)
        color_palette = [(41,48,58,255), (93, 68, 68, 0)]
        if count==2 or card['rarity']=='LEGENDARY':
            xoff = 81
            minx = 105
            maxx = 221
        else:
            xoff = 105
            minx = 129
            maxx = 245
        master.paste(im, (xoff,3+39*index, xoff+130, 39*(index+1)-2))

        gradient = Image.new('RGBA', (width, height))
        draw = ImageDraw.Draw(gradient)
        for x in range(20, minx):
            draw.line([(x, 39*index), (x, 39*(index+1))], fill=color_palette[0])
        for x in range(minx, maxx):
            color = interpolate_color(minx, maxx, x, color_palette)
            draw.line([(x, 39*index), (x, 39*(index+1))], fill=color)
        
        master = Image.alpha_composite(master, gradient)
        draw = ImageDraw.Draw(master)

        font_sizes = cfg[locale]['font_sizes']
        bounds = cfg[locale]['bounds']
        for i in range(len(font_sizes)):
            if len(card['name'])>bounds[i]:
                deck_font_size = font_sizes[i]
                break

        deck_font = 'resources/'+cfg[locale]['deck_font']
        name_font = 'resources/'+cfg[locale]['name_font']
        base = cfg[locale]['base']
        font = ImageFont.truetype(deck_font, deck_font_size)
        draw_shadow(draw, 45, base-deck_font_size/2+39*index, card['name'],font)
        draw.text((45, base-deck_font_size/2+39*index), card['name'], font=font)

        if count==2:
            bg = Image.open(tile_container_number)
            master.paste(bg, (0,39*index, 239, 39*(index+1)), bg)
            font = ImageFont.truetype(number_font, 16)
            w, h = draw.textsize('2', font=font)
            draw.text(((30-w)/2+209,(39-h)/2+39*index), '2', font=font, fill=(229, 181, 68))
        elif card['rarity']=='LEGENDARY':
            bg = Image.open(tile_container_number)
            master.paste(bg, (0,39*index, 239, 39*(index+1)), bg)
            imstar = Image.open(star)
            master.paste(imstar, (214, 39*index+10, 233, 39*index+29), imstar)
        else:
            bg = Image.open(tile_container_open)
            master.paste(bg, (0,39*index, 239, 39*(index+1)), bg)
        msg = str(card['cost'])
        font = ImageFont.truetype(number_font, 25)
        w, h = draw.textsize(msg, font=font)
        draw_shadow(draw,(44-w)/2,(39-h)/2+39*index,str(card['cost']), font)
        draw.text(((44-w)/2, (39-h)/2+39*index), str(card['cost']), font=font)
    if handle is not None:
        font = ImageFont.truetype(number_font, 17)
        handle = handle + ' ' + time.strftime("%Y.%m.%d", time.localtime()) 
        w_h, _ = draw.textsize(handle, font=font)
        draw_shadow(draw, 240-w_h, 39*(index+1)+10, handle ,font)
        draw.text((240-w_h, 39*(index+1)+10), handle, font=font, fill = (255, 255, 255))
    draw = ImageDraw.Draw(master)
    if handle is None:
        decklist = master.crop((0,0,243,39*len(cards)))
        master.paste(decklist, (0,97,243,39*len(cards)+97))
    else:
        decklist = master.crop((0,0,243,39*len(cards)+30))
        master.paste(decklist, (0,97,243,39*len(cards)+97+30))
    master.paste(imclass, (0,0,243,97))
    title = name
    font_locale = ImageFont.truetype(name_font, 24)
    font_en = ImageFont.truetype(number_font, 24)
    _,h_locale = draw.textsize(title, font=font_locale)
    _,h_en = draw.textsize(title, font=font_en)
    w = 0
    for i in range(len(title)):
        if title[i].isdigit() or title[i].islower() or title[i].isupper():
            font = font_en
            aw,_ = draw.textsize(title[i], font=font)
            draw_shadow(draw, 22+w, 72-h_en, title[i], font)
            draw.text((22+w, 72-h_en), title[i], font=font)
        else:
            font = font_locale
            aw,_ = draw.textsize(title[i], font=font)
            draw_shadow(draw, 22+w, 72-h_locale, title[i], font)
            draw.text((22+w, 72-h_locale), title[i], font=font)
        w+=aw
    return master

def merge(imgs):
    width = sum(x.size[0] for x in imgs)
    height = max(x.size[1] for x in imgs)
    master = Image.new('RGBA', (width, height))
    x = 0
    for img in imgs:
        w,h = img.size
        master.paste(img, (x, 0, x+w, h), img)
        x+=w
    return master

def setup_dirs(path):
    if not os.path.exists(path):
        raise Exception('Directory {} does not exist'.format(path))
    if not os.path.isdir(path):
        raise Exception('{} is not a directory'.format(path))
    for x in range(ord('A'),ord('Z')+1):
        addr = '{}/{}'.format(path,chr(x))
        if not os.path.exists(addr):
            os.mkdir(addr)
    addr = '{}/{}'.format(path,'etc')
    if not os.path.exists(addr):
        os.mkdir(addr)

def write_to_csv(deck_dict, code_dest):
    with open(code_dest, 'w') as f:
        for name in deck_dict:
            f.write('{},{}\n'.format(name, ','.join(deck_dict[name])))

def generate_images(deck_dict, dest, ordered=False, locale='enUS', handle=None):
    for name in deck_dict:
        deck_imgs = []
        for deckcode in deck_dict[name]:
            deck = Deck.from_deckstring(deckcode)
            if deck != None:
                if len(deck_imgs)+1==len(deck_dict[name]):
                    img = deck_to_image(deck, name, locale, handle)
                else:
                    img = deck_to_image(deck, name, locale)
                deck_imgs.append(img)
        if len(deck_imgs)==0:
            print('Player {} has no decks'.format(name))
            continue
        img = merge(deck_imgs)
        img = img.convert('RGB')
        name = name.replace('/','\\')
        if ordered:
            if (ord(name[0].upper())>=ord('A') and ord(name[0].upper())<=ord('Z')):
                img.save(u'{}/{}/{}.jpg'.format(dest,name[0].upper(),name), 'JPEG')
            else:
                img.save(u'{}/{}/{}.jpg'.format(dest,'etc',name), 'JPEG')
        else:
            img.save(u'{}/{}.jpg'.format(dest,name), 'JPEG')

def decks_from_csv(decklists, dest, ordered=False, code_dest=None, locale='enUS', handle=None):
    if ordered:
        setup_dirs(dest)
    deck_dict = {}
    with io.open(decklists, "r", encoding="utf-8") as csvfile:
        deckreader = list(csv.reader(csvfile, delimiter=u','))

    schemaLine = deckreader[0]
    schema = []
    key = 0
    start = 1
    for index, x in enumerate(schemaLine):
        if x=='D':
            schema.append('D')
        elif x=='K':
            schema.append('K')
            key = index
        else:
            schema.append('')
    if not any(schema):
        schema = ['K']
        for i in range(len(schemaLine)-1):
            schema.append('D')
        start-=1
    for row in deckreader[start:]:
        name = row[key]
        if name not in deck_dict:
            deck_dict[name] = []
        for index, a in enumerate(schema):
            if a!='D' or index >= len(row):
                continue
            decklist = find_code(row[index])
            deck = parse_deck(decklist)
            if deck!=None:
                # The base64 package that the hearthstone package uses is weird
                # in that it can allow for spaces in the middle of thee deckstring
                # Passing the deckstring directly causes issues when we try to find
                # the deck code from the piece of text when we pass this deckstring
                # back in.
                deck_dict[name].append(deck.as_deckstring)
    if code_dest:
        write_to_csv(deck_dict, code_dest)
    else:
        generate_images(deck_dict, dest, ordered, locale, handle)

def decks_from_battlefy(battlefy_url, dest, ordered=False, code_dest=None, locale='enUS', handle=None):
    if ordered:
        setup_dirs(dest)
    deck_dict = {}
    valid = re.compile(r"^(?:https://)?\/?battlefy.com\/([^:/\s]+)/([^:\/\s]+)/([\w\d]+)/stage/([\w\d]+)/bracket/(\d*)$")
    bracketf= 'https://dtmwra1jsgyb0.cloudfront.net/stages/{}/matches'
    matchf = 'https://dtmwra1jsgyb0.cloudfront.net/matches/{}?extend%5Btop.team%5D%5Bplayers%5D%5Buser%5D=true&extend%5Bbottom.team%5D%5Bplayers%5D%5Buser%5D=true'
    matches = valid.match(battlefy_url)
    if matches is None:
        print("Unable to parse battlefy url. Please get the bracket from the brackets tab")
        return
    groups = matches.groups()
    org = groups[0]
    event = groups[1]
    eventcode = groups[2]
    stagecode = groups[3]
    roundNum = groups[4]
    bracket_url = bracketf.format(stagecode)
    data = json.loads(requests.get(bracket_url).text)
    deck_dict = {}

    for x in data:
        # Check if we need to make an http request by checking if we already have this person's decks
        if not any(['team' in x[i] and x[i]['team']['name'] not in deck_dict for i in ['top', 'bottom']]):
            continue
        r = requests.get(matchf.format(x['_id']))
        matchdata = json.loads(r.text)
        for i in ['top', 'bottom']:
            team = matchdata[0][i]
            if 'team' not in team or team['team']['name'] in deck_dict:
                continue
            name = team['team']['name']
            decks = team['team']['players'][0]['gameAttributes']['deckStrings']
            deck_dict[name] = []
            for decklist in decks:
                deck = parse_deck(decklist)
                if deck!=None:
                    deck_dict[name].append(deck.as_deckstring)
    if code_dest:
        write_to_csv(deck_dict, code_dest)
    else:
        generate_images(deck_dict, dest, ordered, locale, handle)

class SmashHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.extracted = ''

    def handle_data(self, data):
        if data.strip().startswith("window.bootstrappedData="):
            self.extracted = data.strip()[len('window.bootstrappedData='):-1]

def decks_from_smashgg(bracket_url, dest, ordered=False, code_dest=None, locale='enUS', handle=None):
    if ordered:
        setup_dirs(dest)
    deck_dict = {}
    html = requests.get(bracket_url).text
    parser = SmashHTMLParser()
    parser.feed(html)
    data = json.loads(parser.extracted)['dehydratedState']['context']['dispatcher']['stores']
    hero_map = {617:671, 618:274, 619:31, 620:637, 621:813, 622:930,
            623:1066, 624:893, 625:7}
    reverse_map = {}
    for _, card in data['CardStore']['card'].items():
        reverse_map[int(card['id'])] = int(card['externalId'])
    for _, deck in data['CardDeckStore']['cardDeck'].items():
        name = data['EntrantStore']['entrants'][str(deck['entrantId'])]['name']
        cards = {}
        for card in deck['cardIds']:
            if card not in cards:
                cards[card] = 0
            cards[card]+=1
        hero = hero_map[deck['characterIds'][0]]
        deck = Deck()
        deck.heroes = [hero]
        deck.format = FormatType.FT_STANDARD
        deck.cards = [(reverse_map[x], cards[x]) for x in cards]
        if name not in deck_dict:
            deck_dict[name] = []
        deck_dict[name].append(deck.as_deckstring)
    if code_dest:
        write_to_csv(deck_dict, code_dest)
    else:
        generate_images(deck_dict, dest, ordered, locale, handle)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Create deck images from a csv file")
    parser.add_argument('sourceType', choices=['deckcsv', 'battlefy', 'smashgg'], help='The type of source the decklists are from')
    parser.add_argument('source', help='Where to get the decklists from. For the deckcsv option, specify a csv file in your path. For the other 2 options, specify the bracket url of their respective websites')
    parser.add_argument("destination", help='Where the images are generated')
    parser.add_argument("--ordered", help="Set whether images should be grouped by the first letter of the key", action="store_true")
    parser.add_argument("--code-dest", help="When set, output the deck codes to a csv file instead")
    parser.add_argument("--locale", choices=supported_locale, help="The image language", default="enUS")
    parser.add_argument("--watermark", help="The handle of your social account")
    args = parser.parse_args()
    if args.sourceType == 'battlefy':
        decks_from_battlefy(args.source, args.destination, ordered=args.ordered, code_dest=args.code_dest, locale=args.locale, handle=args.watermark)
    elif args.sourceType == 'smashgg':
        decks_from_smashgg(args.source, args.destination, ordered=args.ordered, code_dest=args.code_dest, locale=args.locale, handle=args.watermark)
    else:
        decks_from_csv(args.source, args.destination, ordered=args.ordered, code_dest=args.code_dest, locale=args.locale, handle=args.watermark)

