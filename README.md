# RankTube
This is a python utility that can be used rank videos based on the video's ratio of views to subscribers. The user can input the search term, number of days (recency), and minimum view count.

# Note:
* For the code to work, you must have an YouTube API key. You can get the API key by logging in with your Google ID at https://console.cloud.google.com/apis/ and then going to the Credentials tab. 
* After that, you must add two environment variables: one for YOUTUBE_API (value = API key) and one for LOG_LEVEL (value = DEBUG).
* To run the code just do "python youtube-rating-system.py -st cricket -days 7 -views 10000". You can change any of these values to your liking.
