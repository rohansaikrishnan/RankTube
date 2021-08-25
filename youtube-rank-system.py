import os
import sys
from googleapiclient.discovery import build
import datetime
from datetime import date, timedelta
import decimal
from time import mktime
import json
import logging
import argparse
import csv

#To run the code just do "python test-api.py -st cricket basketball -days 7"

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.__str__()
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        if isinstance(obj, (list, dict, str, int, float, bool, type(None))):
            return JSONEncoder.default(self, obj)
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, decimal.Decimal):
            if obj % 1 > 0:
                return float(obj)
            else:
                return int(obj)
        else:
            return super(MyEncoder, self).default(obj)

try:
    log_level = os.environ['LOG_LEVEL']
    print('log_level: ' + log_level)
except KeyError as error:
    print('LOG_LEVEL not provided. So use INFO level...')
    log_level = logging.INFO

##used only for this testing.
logger = logging.getLogger('test-youtube-api')
logger.setLevel(log_level)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(log_level)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

api_key = os.environ.get("YOUTUBE_API")

def search_videos(args, youtube_api, videos):
    logger.debug('inside search_videos...')

    searchterms = args['searchterm']
    logger.info('searchterms: ' + json.dumps(searchterms))

    search_start_date = datetime.datetime.today() - timedelta(args['numofdays'])
    uploaded_since = datetime.datetime(year=search_start_date.year,month=search_start_date.month,
                           day=search_start_date.day).strftime('%Y-%m-%dT%H:%M:%SZ')

    logger.debug('uploaded_since: ' + json.dumps(uploaded_since))

    
    for term in searchterms:
        logger.debug('obtaining videos for searchterm: ' + term)
        request = youtube_api.search().list(
            part='snippet',
            maxResults=50,
            q=term,
            type='video',
            publishedAfter=uploaded_since
        )
        response = request.execute()
        #logger.debug('response: ' + json.dumps(response, indent=4))
        if 'items' in response:
            for item in response['items']:
                videos.append(item)
    
    logger.debug('Total number of videos across search terms: ' + str(len(videos)))
    return videos
        
def filter_videos(args, youtube_api, all_videos, filtered_videos):
    logger.debug('inside filter_videos...')
    logger.info('number of videos to filter: ' + str(len(all_videos)))

    for i in range(len(all_videos)):
        logger.debug('item: ' + str(i))

        video = all_videos[i]
        logger.debug('item: ' + json.dumps(video))

        video_id = video['id']['videoId']
        logger.debug('video_id: ' + video_id)
        video_stats = youtube_api.videos().list(id=video_id, part='statistics').execute()
        logger.debug('video_stats: ' + json.dumps(video_stats))

        view_count = video_stats['items'][0]['statistics']['viewCount']
        logger.debug('view_count ' + str(view_count) + ' for video ' + video_id)

        if int(view_count) > args['viewcount']:
            video['viewcount'] = view_count
            filtered_videos.append(video)
    
    logger.debug('number of videos in filtered count based on view count ' + str(len(filtered_videos)))
    return filtered_videos
    
def get_channel_info(args, youtube_api, filtered_videos):
    logger.debug('inside get_channel_info...')

    tmp_videos = []
    for  i in range(len(filtered_videos)):
        logger.debug('item: ' + str(i))

        video = filtered_videos[i]
        logger.info('item: ' + json.dumps(video))

        #get the channel id 
        channel_id = video['snippet']['channelId']
        logger.debug('channel_id: ' + channel_id)

        #Get the channel Info
        channelInfo = youtube_api.channels().list(id=channel_id, part='statistics').execute()
        logger.debug('channelInfo: ' + json.dumps(channelInfo))

        #Get channel subscribers, if hiddenSubscriberCount=true then continue to next
        '''
        try:
            subscriber_count = channelInfo['items'][0]['statistics']['subscriberCount']
        except KeyError as exception:
            print("cannot be shown")
            subscriber_count = 0
        '''
        if channelInfo['items'][0]['statistics']['hiddenSubscriberCount']:
            subscriber_count = 1000000
        else:
            subscriber_count = int(channelInfo['items'][0]['statistics']['subscriberCount'])

        logger.debug('subscriber_count ' + str(subscriber_count) + ' for channel ' + channel_id)
        #Add subscribers to the filtered_videos
        video['subscribercount'] = subscriber_count
        tmp_videos.append(video)
        
    
    filtered_videos = tmp_videos
    logger.debug('number of videos in filtered count based on subscriber count ' + str(len(filtered_videos)))
    return filtered_videos
    

def calculate_rating(filtered_videos):
    logger.debug('inside calculate_rating...')
    tmp_videos = []
    for i in range(len(filtered_videos)):
        logger.debug('item: ' + str(i))

        video = filtered_videos[i]
        logger.debug('item: ' + json.dumps(video))

        #get subscriber count
        subscribers = video['subscribercount']

        #get view count
        views = video['viewcount']

        #get published date and today's date
        published_date = video['snippet']['publishedAt']
        d1 = datetime.datetime.strptime(published_date,"%Y-%m-%dT%H:%M:%SZ")
        today_date = datetime.datetime.today()

        #calculate the number of days since video got published
        duration = today_date - d1
        uploaded_since = duration.days
        logger.debug('days_since_published_date ' + str(uploaded_since))

        #if published days is 0 force it to 1
        if uploaded_since == 0:
            uploaded_since = 1

        #create ratio
        ratio = int(views) / int(subscribers)
        logger.debug('ratio ' + str(ratio))

        #create rating - take ratio, multiply by view count, and divide by # of days since video published
        rating = (ratio * int(views)) / int(uploaded_since)
        logger.debug('rating ' + str(rating))

        #add keys to filtered_videos dictionary
        video['days_since_published_date'] = uploaded_since
        video['ratio'] = ratio
        video['rating'] = int(rating)
        tmp_videos.append(video)

    filtered_videos = tmp_videos
    return filtered_videos

def print_ratings(filtered_videos, titles, video_ids, rating):
    logger.debug('inside print_ratings...')
    for i in range(len(filtered_videos)):
        video = filtered_videos[i]
        logger.info('item: ' + json.dumps(video))
        #add rating value to ratings list
        ratings = video['rating']
        rating.append(ratings)
        #add title to title list
        title = video['snippet']['title']
        titles.append(title)
        #add video link to video list
        vid_ids = video['id']['videoId']
        video_ids.append(vid_ids)
        string = "https://www.youtube.com/watch?v="
        video_id = ["{}{}".format(string,i) for i in video_ids ]

    #creating final list of rating, titles, and video link and sorting it based on rating
    z = list(zip(rating, titles, video_id))
    z.sort(key = lambda x: x[0], reverse = True)

    #csv file to show final list
    with open('ratingssystem.csv','a+') as out:
        csv_out=csv.writer(out)
        csv_out.writerows(z)
    return

def lambda_handler(event, context):
    logger.debug('inside lambda_handler...')
    logger.info('received event: ' + json.dumps(event, cls=MyEncoder))
    
    body = json.loads(event['body'])
    logger.info('body: ' + json.dumps(body))
    
    event = body

    youtube_api = build('youtube', 'v3', developerKey=api_key)

    videos = []
    search_videos(event, youtube_api, videos)
    #logger.debug('All Videos: ' + json.dumps(videos, indent=4))
    logger.info('Total number of videos: ' + str(len(videos)))

    filtered_videos = []
    filter_videos(event, youtube_api, videos, filtered_videos)
    get_channel_info(event, youtube_api, filtered_videos)
    calculate_rating(filtered_videos)
    #logger.debug('filtered_videos: ' + json.dumps(filtered_videos))
    logger.info('Total number of filtered videos: ' + str(len(filtered_videos)))

    filtered_videos.sort(key = lambda x:x["rating"], reverse=True)
    logger.debug('filtered_videos: ' + json.dumps(filtered_videos))
    
    #Get the top 5 videos 
    final_list = filtered_videos[:5]
    logger.debug('final_list: ' + json.dumps(final_list))

    display_list = []
    for i in range(len(final_list)):
        item = {}
        video = final_list[i] 
        item['title'] = video['snippet']['title']
        item['url'] = "https://www.youtube.com/watch?v=" + video['id']['videoId']
        item['viewcount'] = video['viewcount']
        item['subscribercount'] = video['subscribercount']
        item['rating'] = video['rating']
        item['publisheddate'] = video['snippet']['publishTime']
        item['channeltitle'] = video['snippet']['channelTitle']
        display_list.append(item)
    logger.debug('display_list: ' + json.dumps(display_list, indent=4))
    
    return {
        'statusCode' : 200,
        'body': json.dumps(display_list)
    }

    '''
    rating = []
    titles = []
    video_ids = []
    print_ratings(filtered_videos, titles, video_ids, rating)
    '''



def main(argv):
    logger.debug('inside main...')
    my_parser = argparse.ArgumentParser(description='List YouTube videos based on my preference')
    my_parser.add_argument('--searchterm', '-st',
                       action='store',
                       type=str,
                       required=True,
                       nargs='+',
                       help='Search Term for the YouTube Video')
    my_parser.add_argument('--numofdays', '-days', 
                       action='store',
                       type=int,
                       required=False,
                       default=7, 
                       help='Number of days old')
    my_parser.add_argument('--viewcount', '-views', 
                       action='store',
                       type=int,
                       required=False,
                       default=5000, 
                       help='Number of days old')
                    
    
    args = my_parser.parse_args()

    print(args) 

    if args.numofdays < 0  or args.numofdays > 365:
        logger.error('Number of days must be between 1 and 365...')
        return 

    event = {}
    body = {}
    body['numofdays'] = args.numofdays
    body['searchterm'] = args.searchterm
    body['viewcount'] = args.viewcount 
    
    event['body'] = json.dumps(body)

    lambda_handler(event, None)

   

if __name__ == "__main__":
    main(sys.argv[1:])