import json
import webhook_listener
from discord_webhook import DiscordWebhook,DiscordEmbed
import pprint
import requests
import time
import configparser
from ipstack import GeoLookup

# parse config file
config = configparser.ConfigParser()
config.read('config.ini')

# globals
discord_webhook_url = config['discord']['url']
geo_lookup = GeoLookup(config['geolookup']['api'])
plex_authtoken=config['plex']['token']
plex_url_header=config['plex']['url']

def process_post_request(request, *args, **kwargs):
    # check user agent header - send to proper function handler
    agent = request.headers['User-Agent']
    if agent.startswith("PlexMediaServer"):
        # plex
        print("This is a Plex webhook\n")
        handle_plex_wh(kwargs)
        return
    elif agent.startswith("Ombi"):
        # ombi
        print("This is an Ombi webhook\n")
        handle_ombi_wh(request)
        return
    elif agent.startswith("Sonarr") or agent.startswith("Radarr"):
        # sonarr/radarr?
        print("This is a Sonarr/Radarr webhook\n")
        handle_arr_wh(request)
        return
    else:
        print("Unhandled request type: {}".format(agent))


def handle_ombi_wh(request):
    # read body of msg, convert to json dict
    body = request.body.read(int(request.headers["Content-Length"]))
    req = json.loads(body)
    print(req)
    format_ombi_event(req)


def handle_arr_wh(request):
    # read body of msg, convert to json dict
    body = request.body.read(int(request.headers["Content-Length"]))
    req = json.loads(body)
    print(req)

def handle_plex_wh(keyword_args):
    # load request
    keyword_args_json = json.loads(keyword_args['payload'])

    # get event type
    event = keyword_args_json['event']

    # case for different POST options
    if event.startswith("media"):
        format_playback_event(keyword_args_json, event)
    elif event.startswith("library"):
        # format_content_event(keyword_args_json,event)
        return
    elif event.startswith("admin") or event.startswith("device") or event.startswith("playback"):
        # format_owner_event(keyword_args_json,event)
        return
    else:
        print("Unknown payload type: {}".format(event))
        return

def format_radarr_event(payload):
    # if root is movie
    movie_info = payload['movie']
    release_info = payload['release']
    remote_movie_info = payload['remoteMovie']
    event_type = payload['eventType']
    return

def format_sonarr_event(payload):
    # if root is episodes
    episode_info = payload['episodes']
    release_info = payload['release']
    event_type = payload['eventType']
    series_info = payload['series']
    title = payload['title']
    path = payload['path']
    tvID = payload['tvdbId']
    return

def format_ombi_event(payload):
    # post data to Discord webhook
    webhook = DiscordWebhook(url=discord_webhook_url)

    # get data
    notificationType = payload['notificationType']
    eventTitle = payload['applicationName']
    thumbnail = payload['posterImage']
    requested_user = payload['requestedUser']
    media_title = payload['title']
    date_req = payload['requestedDate']
    media_type = payload['type']
    summary = payload['overview']
    year = payload['year']

    # media or TV?
    if media_type == "Movie":
        if notificationType == "RequestDeclined":
            requestType = "Movie Request Decline"
        else:
            requestType = "Movie Request"
    elif media_type == "Tv show":
        if notificationType == "RequestDeclined":
            requestType = "TV Show Request Declined"
        else:
            requestType = "TV Show Request"
        # episodes = payload['episodesList']
        seasons = payload['seasonsList']
    else:
        print("Unknown Media Type: {}".format(media_type))
        requestType = "Unknown Media Type"

    # create embed object for webhook
    embed = DiscordEmbed(title=eventTitle, description=requestType, color=242424)
    embed.set_thumbnail(url="http://raw.githubusercontent.com/linuxserver/docker-templates/master/linuxserver.io/img/ombi.png")
    embed.set_image(url=thumbnail)
    embed.set_author(name="Soot Gremlin",url="https://github.com/D3ezy",icon_url="https://avatars.githubusercontent.com/u/32646503?s=400&u=9f02fae3237ee64b1ceb853d37722c67ce4f8338&v=4")
    embed.add_embed_field(name='Title',value=media_title)
    embed.add_embed_field(name='Release Year',value=year)
    embed.add_embed_field(name='User',value=requested_user, inline=False)
    embed.add_embed_field(name='Date Requested',value=date_req, inline=False)
    if media_type == "Tv show":
        # embed.add_embed_field(name='Episodes(s) Requested',value=episodes, inline=False)
        embed.add_embed_field(name='Season(s) Requested', value=seasons)
    if notificationType == "RequestDeclined":
        reason = payload['denyReason']
        embed.add_embed_field(name='Deny Reason', value=reason, inline=False)
    embed.add_embed_field(name="Summary",value=summary, inline=False)
    embed.set_footer(text='Placeholder', icon_url='https://www.pngkey.com/png/full/910-9103810_plex-media-server-transparent-plex-icon.png')
    embed.set_timestamp()

    # add embed object to webhook
    webhook.add_embed(embed)
    response = webhook.execute()
    return

def format_owner_event(payload_args,event_type):
    # if one of following events:
    # admin.database.backup
    # admin.database.corrupted
    # device.new
    # playback.started
    # do something  
    return

def format_content_event(payload_args, event_type):
    # if one of following events:
    # library.on.deck
    # library.new
    # do something
    return

def format_playback_event(payload_args, event_type):
    
    print("Getting event info...")
    
    # event info
    if event_type == 'media.play':
        eventTitle='Media Started'
    elif event_type == 'media.rate':
        #eventTitle='Media Rating'
        return
    else:
        #eventTitle='Unknown'
        return

    # user account info
    account = payload_args['Account']
    username = account['title']
    thumbnail = account['thumb']

    # player info
    player = payload_args['Player']
    playerTitle = player['title']
    playerIP = player['publicAddress']

    # lookup IP Address in IP Stack
    location = geo_lookup.get_location(playerIP)
    city = location['city']
    state = location['region_code']
    country = location['country_name']
    city_state_country = city + ", " + state + ", " + country

    # metadata
    metadata = payload_args['Metadata']
    mediaType = metadata['librarySectionType']
    mediaSummary = metadata['summary']
    mediaRating = metadata['contentRating']
    mediaReleaseYear = metadata['year']
    mediaTitle = metadata['title']
    artURL = metadata['art']

    # post data to Discord webhook
    webhook = DiscordWebhook(url=discord_webhook_url)

    # create embed object for webhook
    embed = DiscordEmbed(title=eventTitle, description="Placeholder", color=242424)
    embed.set_thumbnail(url=thumbnail)
    embed.set_author(name="Soot Gremlin",url="https://github.com/D3ezy",icon_url="https://avatars.githubusercontent.com/u/32646503?s=400&u=9f02fae3237ee64b1ceb853d37722c67ce4f8338&v=4")
        
    if mediaType == 'movie':
        mediaStudio = metadata['studio']
        # get IMDB Link
        mediaGUID = metadata['guid']
        imdb_code = mediaGUID.split("//",1)[-1].split('?',1)[0]
        imdb_link = "https://www.imdb.com/title/" + imdb_code + "/"

        # get movie art
        artRelativePath = metadata['thumb']
        artFullPath = plex_url_header + artRelativePath + plex_authtoken
        embed.set_image(url=artFullPath)
        embed.add_embed_field(name='Title', value=mediaTitle)
        embed.add_embed_field(name='Studio', value=mediaStudio)
        embed.add_embed_field(name='IMDb Link', value=imdb_link, inline=False)

    elif mediaType == 'show':
        showName = metadata['grandparentTitle']
        season = metadata['parentTitle']
        embed.add_embed_field(name='Episode Name', value=mediaTitle)
        embed.add_embed_field(name='Grandparent Title', value=showName)
        embed.add_embed_field(name='Parent Title', value=season)

    else:
        print("Unknown media type: {}".format(mediaType))

    embed.add_embed_field(name='Release Year', value=mediaReleaseYear)
    embed.add_embed_field(name='Rating', value=mediaRating)
    embed.add_embed_field(name='Summary', value=mediaSummary, inline=False)
    embed.add_embed_field(name='Username', value=username)
    embed.add_embed_field(name='Player Type', value=playerTitle)
    embed.add_embed_field(name='Location', value=city_state_country, inline=False)
    embed.set_footer(text='Placeholder', icon_url='https://www.pngkey.com/png/full/910-9103810_plex-media-server-transparent-plex-icon.png')
    embed.set_timestamp()

    # add embed object to webhook
    webhook.add_embed(embed)
    response = webhook.execute()
    return

def main():
    plex_listener = webhook_listener.Listener(handlers={"POST": process_post_request}, port=8080)
    plex_listener.start()
    while True:
        print("Still alive...")
        time.sleep(300)

if __name__ == "__main__":
    main()