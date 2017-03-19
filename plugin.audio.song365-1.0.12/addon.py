#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, urllib2
from xbmcswift2 import Plugin, xbmcaddon, xbmcgui, xbmc
import xbmcswift2
import requests
import os
import json
from shutil import copyfileobj
import distutils.dir_util
from mutagen.id3 import ID3NoHeaderError
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TMCL, TRCK, COMM, TCON, TYER
from mutagen.easyid3 import EasyID3

plugin = Plugin()

usecostum = plugin.get_setting("custom_directory", bool)
extra_info = plugin.get_setting("extra_info", bool)
noImage = xbmc.translatePath(os.path.join('special://home/addons/plugin.audio.song365',  'resources/art/image_not_available.jpg'))

url = str(plugin.get_setting("main_url", unicode))

@plugin.route('/')
def index():
    items = (
        {'label': 'Search Artist', 'path': plugin.url_for('input_artist')}, 
        {'label': 'Search Song',  'path': plugin.url_for('input_track')}, 
        {'label': 'Search Song in Album',  'path': plugin.url_for('input_albumtrack')}, 
        {'label': 'Search Album',  'path': plugin.url_for('input_album')}, 
        {'label': 'Artist [A - Z]',  'path': plugin.url_for('artistAZ')}, 
        {'label': 'Popular Artists',  'path': plugin.url_for('popular_artists')}, 
        {'label': 'Popular Albums',  'path': plugin.url_for('popular_albums')}, 
        {'label': 'Popular Tracks',  'path': plugin.url_for('popular_tracks')}, 
    )
    return items

@plugin.route('/input/<label>', name='input_artist',  options={'label': 'artist'})
@plugin.route('/input/<label>', name='input_track',  options={'label': 'track'})
@plugin.route('/input/<label>', name='input_albumtrack',  options={'label': 'albumtrack'})
@plugin.route('/input/<label>', name='input_album',  options={'label': 'album'})
def input (label) :
    if label == 'artist' :
        t1 = 'Künstlers'
    elif label == 'album' :
        t1 = 'Albums'
    else :
        t1 = 'Liedes'
    text = 'Bitte den Namen des {0} eingeben'.format (t1)
    ep = 'search_{0}_result'.format(label)
    query = plugin.keyboard(heading=(text))
    if query:
        u = plugin.url_for(endpoint = ep, search_string = query)
        plugin.redirect( u )

@plugin.route('/search/<label>/<search_string>',  name='search_artist_result', options={'label' : 'artist'})
@plugin.route('/search/<label>/<search_string>',  name='search_track_result', options={'label' : 'track'})
@plugin.route('/search/<label>/<search_string>',  name='search_albumtrack_result', options={'label' : 'albumtrack'})
@plugin.route('/search/<label>/<search_string>',  name='search_album_result', options={'label' : 'album'})
def search_result ( label, search_string ):
    if label == 'artist' :
        items = get_search_artist(search_string)
    elif label == 'track' :
        items = get_search_track(search_string)
    elif label == 'albumtrack' :
        items = get_search_albumtrack(search_string)
    else :
        items = get_search_album(search_string)
    items = sorted (items, key=lambda item:item['label'])
    return plugin.finish ( items )

@plugin.route('/search/artist_albums/<artist>/<albenurl>/')
def search_artist_albums ( artist, albenurl ):
#    items = get_cached(get_search_albums, artist, albenurl, TTL=1440 )
    items = get_search_artist_albums (artist, albenurl )
#    finish_kwargs = {
#        'sort_methods': [
#            'UNSORTED', 
#            'DATE', 
#            'ALBUM',
#            ('LABEL', '%X'),
#        ],
#    }
#    return plugin.finish ( items, **finish_kwargs)
    return plugin.finish ( items )

@plugin.route('/artistAZ/')
def artistAZ():
    List = set('#ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    items=[]
    for i in List:
        items.append ({
            'label': i, 
            'path': plugin.url_for('get_ArtistAZ',  char=i),
        })
    sorted_items = sorted (items,  key=lambda item:item['label'])
    return plugin.finish ( sorted_items )

@plugin.route('/artistAZ/<char>')
def get_ArtistAZ(char):
    items = get_cached(get_ArtistAZ_List, char, TTL=1440)
    sorted_items = sorted (items,  key=lambda item:item['label'])
    finish_kwargs = {
        'sort_methods': [
            'title',
            'genre',
            ('LABEL', '%X'),
        ],
    }
    return plugin.finish ( sorted_items, **finish_kwargs)

@plugin.route('/popular/artists')
def popular_artists():
    items = get_cached(get_popular_artists,  TTL=1440)
    finish_kwargs = {
        'sort_methods': [
            'UNSORTED', 
            'ARTIST', 
            'GENRE',
            ('LABEL', '%X'),
        ],
    }
    return plugin.finish ( items, **finish_kwargs)

@plugin.route('/popular/albums')
def popular_albums():
    items = get_cached(get_popular_albums,  TTL=1440)
    finish_kwargs = {
        'sort_methods': [
            'UNSORTED', 
            'ARTIST', 
            'ALBUM',
            'GENRE',
            ('LABEL', '%X'),
        ],
    }
    return plugin.finish ( items, **finish_kwargs)
#    return plugin.finish ( items )

@plugin.route('/popular/tracks/')
def popular_tracks():
    items = get_cached(get_popular_tracks, TTL=1440)
    finish_kwargs = {
        'sort_methods': [
            'UNSORTED', 
            'ARTIST', 
            'ALBUM',
            'GENRE',
            ('LABEL', '%X'),
        ],
    }
    return plugin.finish ( items, **finish_kwargs)

@plugin.route('/search/<albenurl>/<albenname>/<thumb>')
def search_album_title ( albenurl, albenname, thumb ):
    items = get_cached(get_search_album_title, albenurl, albenname, thumb, TTL=1440)
#    return plugin.finish(items)
    finish_kwargs = {
        'sort_methods': [
            'UNSORTED', 
            'ARTIST', 
            'ALBUM',
#            'TRACK',
            ('LABEL', '%X'),
        ],
    }
    return plugin.finish ( items, **finish_kwargs)

@plugin.route('/copy/track/<src>/<ziel>/<artist>/<genre>/<year>/<album>/<no>/<title>')
def copy_track (src, ziel, artist, genre, year, album, no, title):
    fn = '{0} - {1} - {2}.mp3'.format(no, artist, title)
    ziel = os.path.abspath(ziel)
    f = copy_file (src, ziel, fn )
    if f:
        write_mp3Tag(f, artist, year, album, no, '', title,  genre, '')
        dialog('Track in {0} kopiert'.format(ziel))
    else:
        dialog('Track wurde nicht gefunden')        
    return

@plugin.route('/copy/album/<albenurl>')
def copy_album (albenurl):
    pDialog = xbmcgui.DialogProgressBG()
    pDialog.create('Download Album ', 'Get Data...')
    AlbumData = _get_album_title (albenurl)
    y = len(AlbumData['tracks'])
    x = 0
    AlbumData['artist'] = forbidden_char(AlbumData['artist'])
    AlbumData['album'] = forbidden_char(AlbumData['album'])
    d = dst + AlbumData['artist']+'/'+'('+AlbumData['year']+') '+AlbumData['album']
    adata = get_albumdata (AlbumData['album'],  AlbumData['artist'])
    if adata:
        cover = adata['strAlbumThumb']
        if adata['strGenre']:
            AlbumData['genre'] = adata['strGenre']
        if adata['strArtist']:
            AlbumData['artist'] = adata['strArtist']
        if adata['strAlbum']:
            AlbumData['album'] = adata['strAlbum']
        if adata['intYearReleased']:
            AlbumData['year'] = adata['intYearReleased']
        if cover:
            copy_file (cover, d, 'folder.{0}'.format(cover.split('.')[-1]))

    for data in AlbumData['tracks']:
        if data['path'][-4:].lower() == '.mp3':
            x += 1
            z = int(float(x) / y * 100)
            pDialog.update (z, 'Download Album - {0} '.format(AlbumData['album']), 'Copy : {0}. {1}'.format(data['no'], data['title'] ))
            fn = '{0} - {1} - {2}.mp3'.format(data['no'], AlbumData['artist'] , data['title'])
            fname = copy_file (data['path'], d, fn )
            if fname:
                mp3_tags(fname, AlbumData['artist'], AlbumData['year'], AlbumData['album'], data['no'], AlbumData['tracks'], data['title'],  AlbumData['genre'], AlbumData['comment'])
    pDialog.close()
    return

def get_ArtistAZ_List(char):
    pDialog = xbmcgui.DialogProgressBG()
    pDialog.create('Get Artist Data', 'Get Data...')
    if char == '#':
        Path = '/artist-digital.html'
    else:
        Path = '/artist-{0}.html'.format(char)
    content = open_url(url+Path)
    HList = regex_from_to(content,'<div class="list">', '<div class="item">', excluding=True)
    HotList = regex_get_all(HList,'<a href="', '</a>', excluding=False)
    List = regex_get_all(content,'<div class="item"><span>', '</span>', excluding=True)
    items = []
    for i in HotList:
        try:
            infoArtist = del_em(regex_from_to(i, '/>', '</a>'))
        except:
            __log('infoArtist : {0}'.format(i))
        else:
            infoPath = regex_from_to(i, '<a href="', '"').replace('/artist/' , '/artist/albums/')
            items.append ({
                'label': infoArtist, 
                'path': plugin.url_for('search_artist_albums', artist= infoArtist, albenurl = infoPath ), 
                'thumbnail': None, 
                'info': {
                    'artist': infoArtist, 
                    'genre': None, 
                    'comment': None, 
                }, 
            })
    for i in List:
        try:
            infoArtist = del_em(regex_from_to(i, 'class="link">', '</a>'))
        except:
            __log('infoArtist : {0}'.format(i))
        else:
            infoPath = regex_from_to(i, '<a href="', '"').replace('/artist/' , '/artist/albums/')
            items.append ({
                'label': infoArtist, 
                'path': plugin.url_for('search_artist_albums', artist= infoArtist, albenurl = infoPath ), 
                'thumbnail': None, 
                'info': {
                    'artist': infoArtist, 
                    'genre': None, 
                    'comment': None, 
                }, 
            })
    if extra_info:
        i = 0
        x = 0
        y = len(items)
        for Data in items:
            x += 1
            z = int(float(x) / y * 100)
            pDialog.update (z, 'Get Extra Data ', 'Artist : {0}'.format(Data['info']['artist']))
            ExtraData = get_artistdata(Data['info']['artist'])
            if ExtraData:
                if ExtraData['strArtistThumb']: items[i]['thumbnail'] = ExtraData['strArtistThumb']
                if ExtraData['strBiographyDE']: items[i]['info']['comment'] = ExtraData['strBiographyDE']
                else :
                    if ExtraData['strBiographyEN']: items[i]['info']['comment'] = ExtraData['strBiographyEN']
                if ExtraData['strGenre'] and len (ExtraData['strGenre']) >0 :
                    items[i]['info']['genre'] = ExtraData['strGenre']
                    items[i]['label'] = '{0} [{1}]'.format(Data['info']['artist'], ExtraData['strGenre'])
            i += 1
    pDialog.close()
    return (items)
    
def get_popular_tracks():
    pDialog = xbmcgui.DialogProgressBG()
    pDialog.create('Get Track Data', 'Get Data...')
    content = open_url(url)
    __log(content)
    content = regex_from_to(content, '<div class="index-songs-artist">', '<div class="hot-artist">')
    List = regex_get_all(content, '<div class="item', '</div>')
    __log(List)
    items = []
    x = 0
    y = len(List)
    for i in List:
        x += 1
        z = int(float(x) / y * 100)
        infoAnker = regex_get_all(i,'<a href="', '</a>', excluding=False)
        infoArtist = del_em(regex_from_to(infoAnker[1], '<a href=".*">', '</a>')).strip() 
        infoSong = del_em(regex_from_to(infoAnker[0], '<a href=".*">', '</a>')).strip() 
        infoPath = regex_from_to(infoAnker[0], '<a href="', '"').replace('/track', '/download')
        pDialog.update (z, 'Get Track Data ', 'Artist : {0}'.format(infoArtist))
        infoURL = catch_download( url + infoPath)
        if infoURL[-4:].lower()=='.mp3':
            items.append ({
                'label' : '{0} - {1}'.format(infoArtist, infoSong), 
                'path': infoURL,
                'info' : {
                    'tracknumber' : None,  
                    'discnumber' : None, 
                    'duration' : None, 
                    'year' : None, 
                    'genre' : None, 
                    'album' : None,
                    'artist' : infoArtist, 
                    'title' : infoSong, 
                    'rating' : None, 
                    'comment' : None, 
                }, 
                'thumbnail': noImage, 
                'is_playable': True,
            })
    if extra_info:
        i = 0
        x = 0
        y = len(items)
        for item in items:
            x += 1
            z = int(float(x) / y * 100)
            pDialog.update (z, 'Get Extra Data ', 'Artist : {0}'.format(item['info']['artist']))
            Data = get_trackdata (item['info']['artist'],  item['info']['title'])
            if Data :
                if Data['strAlbum']: items[i]['info']['album'] = Data['strAlbum']
                if Data['intTrackNumber'] : items[i]['info']['tracknumber'] = Data['intTrackNumber']
                if Data['strGenre'] :
                    items[i]['info']['genre'] = Data['strGenre']
                    items[i]['label'] = '{0} - {1} [{2}]'.format(infoArtist, infoSong, Data['strGenre'])
                if Data['idAlbum'] :
                    AlbumData = get_albumdata_id (Data['idAlbum'])
                    if AlbumData :
                        if AlbumData['intYearReleased'] : items[i]['info']['year'] = AlbumData['intYearReleased']
                        if AlbumData['strAlbumThumb'] : items[i]['thumbnail'] = AlbumData['strAlbumThumb']
            i += 1
    pDialog.close()
    return ( items )

def get_popular_albums():
    pDialog = xbmcgui.DialogProgressBG()
    pDialog.create('Album Data', 'Get Data...')
    content = open_url(url +'/album/week.html')
    content = regex_from_to(content, '<div class="albums">', '<div class="copyright">')
    List = regex_get_all(content, '<div class="item', ' </div>')
    items = []
    for i in List:
        infoAnker = regex_get_all(i,'<a href="', '</a>', excluding=False)
        infoAlbum = del_em(regex_from_to(infoAnker[1], '<a href=".*">', '</a>'))
        infoThumb = regex_from_to(infoAnker[0], '<img src="', '"')
        infoPath = regex_from_to(infoAnker[1], '<a href="', '"')

        infoYear = infoAlbum[-5:].replace(')', '')
        infoAlbum = infoAlbum[:len(infoAlbum)-7]

        context_menu = []
        context_menu.append(('[COLOR lime]Download Album[/COLOR]',
            'XBMC.RunPlugin(%s)' % plugin.url_for('copy_album',  albenurl = infoPath)))
        items.append ({
            'label': '({0}) {1}'.format(infoYear, infoAlbum), 
            'path': plugin.url_for('search_album_title', albenurl = infoPath, albenname='('+infoYear+') '+infoAlbum,  thumb=infoThumb ),
            'info': {
                'genre' : None, 
                'artist' : None,
                'year' : infoYear,
                'album' : infoAlbum, 
            }, 
            'thumbnail':  infoThumb,
            'context_menu' : context_menu,
        })
    if extra_info:
        i = 0
        x = 0
        y = len(items)
        for item in items:
            x += 1
            z = int(float(x) / y * 100)
            pDialog.update (z, 'Get Extra Data ', 'Album : {0}'.format(item['info']['album']))
            Data = get_albumdata_by_Name (item['info']['album'])
            if Data :
                for ye in Data:
                    if ye['intYearReleased']:
                        if ye['intYearReleased'] == items[i]['info']['year'] :
                            if ye['strAlbum']: items[i]['info']['album'] = ye['strAlbum']
                            if ye['strGenre'] :
                                items[i]['info']['genre'] = ye['strGenre']
                                items[i]['label'] = '({0}) {1} [{2}]'.format(items[i]['info']['year'],  items[i]['info']['album'], ye['strGenre'])
                            if ye['idAlbum'] :
                                AlbumData = get_albumdata_id (ye['idAlbum'])
                                if AlbumData :
                                    if AlbumData['intYearReleased'] : items[i]['info']['year'] = AlbumData['intYearReleased']
                                    if AlbumData['strAlbumThumb'] : items[i]['thumbnail'] = AlbumData['strAlbumThumb']
            i += 1
    pDialog.close()            
    return ( items )

def get_popular_artists():
    pDialog = xbmcgui.DialogProgressBG()
    pDialog.create('Artist Data', 'Get Data...')
    content = open_url(url +'/artist.html')
    content = regex_from_to(content, '<div class="list">', '</div>')
    List = regex_get_all(content, '<a href="', '</a>')
    items = []
    for i in List:
        infoPath = regex_from_to(i, '<a href="', '"').replace('artist', 'artist/albums')
        infoThumb = regex_from_to(i, '<img src="', '"')
        infoArtist = del_em(regex_from_to(i, '/>', '</a>'))
        context_menu = []
        items.append ({
            'label': infoArtist, 
            'path': plugin.url_for('search_artist_albums', artist= infoArtist, albenurl = infoPath ),
            'info': {
                'genre' : None, 
                'artist' : infoArtist,
                'year' : None,
                'album' : None, 
            }, 
            'thumbnail':  infoThumb,
            'context_menu' : context_menu,
        })
    if extra_info:
        i = 0
        x = 0
        y = len(items)
        for item in items:
            x += 1
            z = int(float(x) / y * 100)
            pDialog.update (z, 'Get Extra Data ', 'Artist : {0}'.format(item['info']['artist']))
            ArtistData = get_artistdata (item['info']['artist'])
            if ArtistData:
                if ArtistData['strArtistThumb']: items[i]['thumbnail'] = ArtistData['strArtistThumb']
                if ArtistData['strGenre'] :
                    items[i]['info']['genre'] = ArtistData['strGenre']
                    items[i]['label'] += ' [{0}]'.format(ArtistData['strGenre'])
            i += 1
    pDialog.close()            
    return ( items )

def get_search_artist ( search_string ) :
    content = open_url(url + '/search/artist?keyword='+search_string)
    List = regex_get_all(content, '<div class="item', ' </div>')
    items = []
    for i in List:
        infoAnker = regex_get_all(i,'<a href="', '</a>', excluding=False)
        infoArtist = del_em(regex_from_to(infoAnker[1], '<a href=".*">', '</a>')).strip() 
        infoPath = regex_from_to(infoAnker[0], '<a href="', '"').replace('/artist/' , '/artist/albums/')
        infoThumb = regex_from_to(infoAnker[0], '<img src="', '"')
        ArtistData = get_artistdata (infoArtist)
        if ArtistData:
            if ArtistData['strArtistThumb']: infoThumb = ArtistData['strArtistThumb']
        items.append ({
            'label':infoArtist, 
            'path': plugin.url_for('search_artist_albums', artist= infoArtist, albenurl = infoPath ),
            'thumbnail': infoThumb, 
        })
    return (items)

def get_search_track ( search_string ) :
    content = open_url(url + '/search/track?keyword='+search_string)
    List = regex_get_all(content, '<div class="item', ' </div>')
    items = []
    for i in List:
        infoAnker = regex_get_all(i,'<a href="', '</a>', excluding=False)
        infoArtist = del_em(regex_from_to(infoAnker[1], '<a href=".*">', '</a>')).strip() 
        infoSong = del_em(regex_from_to(infoAnker[0], '<a href=".*">', '</a>')).strip() 
        infoAlbum = del_em(regex_from_to(infoAnker[2], '<a href=".*">', '</a>')).strip() 
        infoSongPath = regex_from_to(infoAnker[0], '<a href="', '"').replace ('/track', '/download')

        dstTrack = dst+forbidden_char(infoArtist)+ '/' + forbidden_char(infoAlbum)

        infoTrackPath = catch_download( url + infoSongPath)
        context_menu = []

        if infoTrackPath[-4:].lower() == '.mp3':
            context_menu.append(('[COLOR lime]Download Track[/COLOR]',
                'XBMC.RunPlugin(%s)' % plugin.url_for('copy_track',
                    src = infoTrackPath, 
                    ziel = dstTrack,
                    artist = infoArtist, 
                    genre = 'pop', 
                    year = '1900', 
                    album = infoAlbum, 
                    no = '00', 
                    title = infoSong, )))
            items.append ({
                'label':infoArtist + ' - ' + infoAlbum + ' | ' + infoSong, 
                'path': infoTrackPath,
                'thumbnail' : noImage, 
                'context_menu' : context_menu, 
                'is_playable': True,
            })
    return (items)

def get_search_albumtrack ( search_string ) :
    content = open_url(url + '/search/track?keyword='+search_string)
    List = regex_get_all(content, '<div class="item', ' </div>')
    items = []

    for i in List:
        infoAnker = regex_get_all(i,'<a href="', '</a>', excluding=False)
        infoArtist = del_em(regex_from_to(infoAnker[1], '<a href=".*">', '</a>')).strip() 
        infoSong = del_em(regex_from_to(infoAnker[0], '<a href=".*">', '</a>')).strip() 
        infoAlbum = del_em(regex_from_to(infoAnker[2], '<a href=".*">', '</a>')).strip() 
        infoAlbumPath = regex_from_to(infoAnker[2], '<a href="', '"')
        context_menu = []
        context_menu.append(('[COLOR lime]Download Album[/COLOR]',
            'XBMC.RunPlugin(%s)' % plugin.url_for('copy_album',  albenurl = infoAlbumPath)))

        items.append ({
            'label':infoArtist + ' - ' + infoAlbum + ' | ' + infoSong, 
            'path': plugin.url_for('search_album_title', albenurl = infoAlbumPath, albenname=infoAlbum,  thumb = noImage), 
            'thumbnail': noImage, 
            'context_menu' : context_menu, 
        })
    return (items)

def get_search_album ( search_string ) :
    content = open_url(url + '/search/album?keyword='+search_string)
    List = regex_get_all(content, '<div class="item', ' </div>')
    items = []
    for i in List:
        infoAnker = regex_get_all(i,'<a href="', '</a>', excluding=False)
        infoAlbum = del_em(regex_from_to(infoAnker[1], '<a href=".*">', '</a>')).strip() 
        infoArtist = del_em(regex_from_to(infoAnker[2], '<a href=".*">', '</a>')).strip() 
        infoYear= '(' + regex_from_to( i, '<div class="release-date">', '</div>')[-4:] + ') '
        infoPath = regex_from_to(infoAnker[1], '<a href="', '"')
        infoThumb =  regex_from_to(infoAnker[0], '<img src="', '"')
        t = _get_albumcover (infoAlbum, infoArtist)
        if t:
            infoThumb = t
        context_menu = []
        context_menu.append(('[COLOR lime]Download Album[/COLOR]',
            'XBMC.RunPlugin(%s)' % plugin.url_for('copy_album',  albenurl = infoPath)))

        items.append ({
            'label': infoArtist +' - ' + infoYear + infoAlbum, 
            'path': plugin.url_for('search_album_title', artist= infoArtist,  albenurl = infoPath,  albenname=infoAlbum,  thumb=infoThumb),
            'thumbnail':  infoThumb, 
            'context_menu' : context_menu, 
        })
    return (items)

def get_search_artist_albums ( artist, albenurl ):
    content = open_url ( url+ albenurl )
    Alben = None
    Alben = regex_get_all ( content, '<div class="item', ' </div>' )
    items = []
    if Alben:
        for i in Alben:
            infoAnker = regex_get_all( i, '<a href="/album', '</a>', excluding=False )
            if infoAnker:
                infoPath = regex_from_to( infoAnker[0], '<a href="', '"' )
                infoAlbum = del_quotes( regex_from_to( infoAnker[1], '<a href=".*">', '</a>' ) ).strip() 
                infoThumb = regex_from_to( infoAnker[0], '<img src="', '"' )
                t = _get_albumcover (infoAlbum, artist)
                if t:
                    infoThumb = t
                try:
                    infoYear= regex_from_to( i, '<em class="release-date">', '</em>')
                except:
                    infoYear = ''
                else:
                    infoYear = '(' + infoYear[-4:] + ') '
                if infoAlbum == None:
                    sorted_items = sorted (items, key=lambda item:item['label'])
                    return plugin.finish ( sorted_items )
            else:
                sorted_items = sorted (items, key=lambda item:item['label'])
                return plugin.finish ( sorted_items )
            
            context_menu = []
            context_menu.append(('[COLOR lime]Download Album[/COLOR]',
                'XBMC.RunPlugin(%s)' % plugin.url_for('copy_album',  albenurl = infoPath)))
    
            items.append ({
                'label': infoYear+infoAlbum, 
                'path': plugin.url_for('search_album_title',artist=artist, albenurl = infoPath, albenname=infoAlbum,  thumb=infoThumb),
                'info':{
                    'tracknumber' : None, 
                    'duration' : None, 
                    'year' : infoYear[-5:4], 
                    'genre' : None, 
                    'album' : infoAlbum, 
                    'artist' : artist, 
                    'title' : None, 
                    'rating' : None, 
                    'lyrics' : None, 
                    'playcount' : None, 
                    'lastplayed' : None, 
                }, 
#                'info_type' : 'audio', 
                'replace_context_menu' : True, 
                'thumbnail':  infoThumb,
                'context_menu' : context_menu, 
            })
    sorted_items = sorted (items, key=lambda item:item['label'])
    return (sorted_items)

def get_search_album_title ( albenurl, albenname, thumb ):
    AlbumData = _get_album_title (albenurl)
    t = _get_albumcover (AlbumData['album'], AlbumData['artist'])
    if t:
        AlbumData['thumb'] = t
    items = []

    dstTrack = dst+forbidden_char(AlbumData['artist'])+'/'+'('+AlbumData['year']+') '+forbidden_char(AlbumData['album'])
    for data in AlbumData['tracks']:
        context_menu = []
        context_menu.append(('[COLOR lime]Download Track[/COLOR]',
            'XBMC.RunPlugin(%s)' % plugin.url_for('copy_track',
                src = data['path'], 
                ziel = dstTrack,
                artist = AlbumData['artist'], 
                genre = AlbumData['genre'], 
                year = AlbumData['year'], 
                album = AlbumData['album'], 
                no = data['no'], 
                title = data['title'], )))
                
        context_menu.append(('[COLOR lime]Download Album[/COLOR]',
            'XBMC.RunPlugin(%s)' % plugin.url_for('copy_album',  albenurl = albenurl)))
        if data['path'][-4:].lower() == '.mp3':
            items.append ({
                'label': data['no']+'. '+data['title'],  
                'path': data['path'],
                'thumbnail': AlbumData['thumb'], 
                'info': {
                    'tracknumber' : data['no'],  
                    'discnumber' : '', 
                    'duration' : '', 
                    'year' : AlbumData['year'], 
                    'genre' : AlbumData['genre'], 
                    'album' : AlbumData['album'],
                    'artist' : AlbumData['artist'], 
                    'title' : data['title'], 
                    'rating' : '0', 
                    'comment' : AlbumData['comment'], 
                }, 
                'replace_context_menu' : True, 
                'context_menu': context_menu,
                'is_playable': True,
            })
    return (items)

def copy_file (src, ziel,  fname):
    global dump
    c = None
    fname = forbidden_char(fname)
    try:
        file = requests.get(src, stream=True)
    except:
        __log('Kann URL nicht öffnen : {0}'.format(src))
    else:
        dump = file.raw
        x = os.path.abspath(ziel + '/' + fname)
        y = os.path.abspath(ziel)
        distutils.dir_util.mkpath(y)
        with open(x, 'wb') as f:
            copyfileobj(dump, f)
        del dump
        c = x
    return (c)

def forbidden_char(string):
    forbidden_chars = set('<>:"/\|?*')
    for c in forbidden_chars:
        string = string.replace(c, '_')
    return (string)

def dialog (info):
    __addon__ = xbmcaddon.Addon()
    __icon__ = __addon__.getAddonInfo('icon')
    plugin.notify (msg=info, delay=1000, image=__icon__)

def _get_albumcover (album,  artist):
    p = None
    coverurl = 'http://www.theaudiodb.com/api/v1/json/1/searchalbum.php?s={0}&a={1}'.format(artist, album).replace(' ', '%20')
    __log (coverurl)
    try:
        f = urllib2.urlopen(coverurl)
    except:
        pass
    else:
        json_string = f.read()
        f.close()
        try:
            parsed_json = json.loads(json_string)
        except:
            pass
        else:
            __log (parsed_json)
            if parsed_json['album']:
                __log (parsed_json['album'][0]['strAlbumThumb'])
                p = parsed_json['album'][0]['strAlbumThumb']
    return (p)

def get_albumdata (album,  artist):
    p = None
#    if extra_info == 'true':
    coverurl = 'http://www.theaudiodb.com/api/v1/json/1/searchalbum.php?s={0}&a={1}'.format(artist, album).replace(' ', '%20')
    __log (coverurl)
    try:
        f = urllib2.urlopen(coverurl)
    except:
       pass
    else:
        json_string = f.read()
        f.close()
        try:
            parsed_json = json.loads(json_string)
        except:
            pass
        else:
            __log (parsed_json)
            if parsed_json['album']:
#                __log (parsed_json['album'][0]['strAlbumThumb'])
                p = parsed_json['album'][0]
    return (p)

def get_albumdata_by_Name (album):
    p = None
    coverurl = 'http://www.theaudiodb.com/api/v1/json/1/searchalbum.php?a={0}'.format(album).replace(' ', '%20')
    __log (coverurl)
    try:
        f = urllib2.urlopen(coverurl)
    except:
       pass
    else:
        json_string = f.read()
        f.close()
        try:
            parsed_json = json.loads(json_string)
        except:
            pass
        else:
            __log (parsed_json)
            if parsed_json['album']:
                p = parsed_json['album']
    return (p)

def get_albumdata_id (id):
    p = None
    coverurl = 'http://www.theaudiodb.com/api/v1/json/1/album.php?m={0}'.format(id)
    __log (coverurl)
    try:
        f = urllib2.urlopen(coverurl)
    except:
       pass
    else:
        json_string = f.read()
        f.close()
        try:
            parsed_json = json.loads(json_string)
        except:
            pass
        else:
            __log (parsed_json)
            if parsed_json['album']:
#                __log (parsed_json['album'][0]['strAlbumThumb'])
                p = parsed_json['album'][0]
    return (p)

def get_trackdata (artist,  track):
    p = None
#    if extra_info == 'true':
    coverurl = 'http://www.theaudiodb.com/api/v1/json/1/searchtrack.php?s={0}&t={1}'.format(artist, track).replace(' ', '%20')
    __log (coverurl)
    try:
        f = urllib2.urlopen(coverurl)
    except:
       pass
    else:
        json_string = f.read()
        f.close()
        try:
            parsed_json = json.loads(json_string)
        except:
            pass
        else:
            __log (parsed_json)
            if parsed_json['track']:
#                __log (parsed_json['album'][0]['strAlbumThumb'])
                p = parsed_json['track'][0]
    return (p)

def get_artistdata (artist):
    p = None
#    if extra_info == 'true':
    coverurl = 'http://www.theaudiodb.com/api/v1/json/1/search.php?s={0}'.format(artist).replace(' ', '%20')
    __log (coverurl)
    try:
        f = urllib2.urlopen(coverurl)
    except:
       pass
    else:
        json_string = f.read()
        f.close()
        try:
            parsed_json = json.loads(json_string)
        except:
            pass
        else:
            __log (parsed_json)
            if parsed_json['artists']:
#                __log (parsed_json['album'][0]['strAlbumThumb'])
                p = parsed_json['artists'][0]
    return (p)

def _get_trackcover (artist,  song):
    p = None
#    if extra_info == 'true':
    coverurl = 'http://www.theaudiodb.com/api/v1/json/1/searchtrack.php?s={0}&t={1}'.format(artist, song).replace(' ', '%20')
    __log (coverurl)
    try:
        f = urllib2.urlopen(coverurl)
    except:
        pass
    else:
        json_string = f.read()
        f.close()
        try:
            parsed_json = json.loads(json_string)
        except:
            pass
        else:
            __log (parsed_json)
            if parsed_json['track']:
                __log (parsed_json['track'][0]['strTrackThumb'])
                p = parsed_json['track'][0]['strTrackThumb']
    return (p)

def _get_album_title ( albenurl ):
    AlbumData = {}
    content = open_url ( url + albenurl )
    content = regex_from_to ( content, '<div class="album-overview">',  '<div class="artist-album">' )
    HeadData = regex_get_all ( content, 'profile-item-value">', '</em></div>', excluding=True)
    AlbumData['artist'] = del_quotes(regex_from_to ( HeadData[0], '<a href=".*">',  '</a>' )).strip() 
    AlbumData['album'] = del_quotes(regex_from_to ( content, '<b>Tracks Of ', '</b>')).strip() 
    AlbumData['thumb'] = regex_from_to ( content, '<img src="', '"' )
    AlbumData['comment'] = del_quotes( regex_from_to ( content, '<div class="content">',  '</div>').strip() )
    if len ( HeadData ) == 5 :
        AlbumData['genre'] = HeadData [4]
    else:
         AlbumData['genre'] = 'pop'
    AlbumData['year'] = HeadData [3][-4:]
    AlbumData['tracks'] = []
    Titles = regex_get_all ( content, '<div class="item', ' </div>' )
    for i in Titles:
        infoAnker = regex_get_all( i, '<a href="', '</a>', excluding=False )
        __log ('InfoAnker : {0}'.format(infoAnker[3]))
        number = regex_from_to( i,'<div class="number">','</div>')
        number = '00'[ len ( number):] + number
        AlbumData['tracks'].append({
            'title': del_quotes( regex_from_to( infoAnker [0], '<a href=.*>', '<' ) .strip()), 
            'no' : number, 
            'path': catch_download( url + regex_from_to( infoAnker [3], '<a href="', '"' ) ),
        })
    return (AlbumData)
    
def __log(text):
    plugin.log.info(text)

def del_quotes  (text):
    if text:
        text = text.replace ('&#039;', "'")
        text = text.replace ('&#8217;', "'")
        text = text.replace ('&quot;', '"')
        text = text.replace ('&#038;', '&')
        text = text.replace ('&amp;', '&')
    return (text)

def del_em(text):
    if text:
        text = text.replace ('<em>', '')
        text = text.replace ('</em>', '')
        text = del_quotes (text)
    return (text)

def regex_get_all(text,  start_with,  end_with, excluding=False):
    r = None
    if text:
        if excluding:
            r = re.findall("(?i)" + start_with + "([\S\s]+?)" + end_with,  text, flags=0)
        else:
            r = re.findall("(?i)(" + start_with + "[\S\s]+?" + end_with + ")",  text, flags=0)
    return r
    
def regex_from_to(text,  from_string,  to_string,  excluding=True):
    r = None
    if text:
        if excluding:
            r = re.search("(?i)" + from_string + "([\S\s]+?)" + to_string,  text).group(1)
        else:
            r = re.search("(?i)(" + from_string + "[\S\s]+?" + to_string + ")",  text).group(1)
    return r

def catch_download (aurl):
    content = open_url(aurl)
    __log ('URL download : %s' %aurl)
    murl = aurl
    if content:
        try:
            murl = regex_from_to(content, "var hqurl = '","';")
        except:
            __log ('Keine Download URL vorhanden!')
    else:
        __log('Fehler : %s' %aurl)
    return murl
    
def open_url(adr):
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'de-DE,de;q=0.8',
        'Connection': 'keep-alive'}
    req = urllib2.Request(adr, headers=hdr)
    global page
    try:
        page = urllib2.urlopen(req)
    except urllib2.HTTPError as  e:
        __log('url öffnen fehler : %s' %e.fp.read())
        __log('die url lautet : %s' %adr)
    content = page.read()
    page.close
    return content

def mp3_tags(fname, artist, year, album, no, tracks, title, genre, comment):
    try: 
        audio = ID3(fname)
    except ID3NoHeaderError:
        audio = ID3()
    audio.add(TPE1(encoding=3, text=artist))   # Artist Name
    audio.add(TMCL(encoding=3, text=artist))   # Performer
    audio.add(TCON(encoding=3, text=genre))    # Genre
    audio.add(TYER(encoding=3, text=year))   # Year
    audio.add(TALB(encoding=3, text=album))   # Album Name
    audio.add(TRCK(encoding=3, text=unicode(no, 'utf8')))    # Tracknumber
    audio.add(TIT2(encoding=3, text=unicode(title, 'utf8')))    # Titel 
    audio.add(COMM(encoding=3, text=unicode(comment, 'utf8')))    # Comment
    audio.save(fname,v2_version=3)

def write_mp3Tag (fname, artist, year, album, no, tracks, title, genre, comment):
    # create ID3 tag if not present
    try: 
        audio = EasyID3(fname)
    except ID3NoHeaderError:
        audio = EasyID3()
    audio['title'] = unicode(title, 'utf8')
    audio['album']= unicode(album, 'utf8')
    audio['artist'] = unicode(artist, 'utf8')
    audio['performer'] = unicode(artist, 'utf8')
    audio['genre'] = unicode(genre, 'utf8')
    audio['date'] = unicode(year, 'utf8')
    audio['tracknumber'] = unicode(no, 'utf8')
    audio.save(fname,v2_version=3)

def get_cached(func, *args, **kwargs):
    '''Return the result of func with the given args and kwargs
    from cache or execute it if needed'''
    @plugin.cached(kwargs.pop('TTL', 1440))
    def wrap(func_name, *args, **kwargs):
        return func(*args, **kwargs)
    return wrap(func.__name__, *args, **kwargs)

if __name__ == '__main__':
    if usecostum:
        dst = plugin.get_setting("music_dir")
    else:
        dst = os.path.expanduser('~/music/')
    if not extra_info: plugin.clear_function_cache()
    __log ('sort metoden : {0}'.format(dir(xbmcswift2.SortMethod)))
    plugin.run()
