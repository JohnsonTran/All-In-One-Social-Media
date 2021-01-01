from datetime import datetime

class Post:
    def __init__(self, social_media, time_posted, embed, is_cached=False):
        self.social_media = social_media
        time_str = self.normalize_datetime(time_posted)
        self.time_posted = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        self.embed = embed

    # change the datetime of posts to be YYYY-MM-DD HH:MM:SS
    # instagram:    2020-12-17T06:15:32.000Z
    # twitter:      2020-12-18 20:08:51
    # youtube:      2020-11-10T04:54:51Z
    #
    # Celery:
    # instagram:    2020-12-17T06:15:32.000Z
    # twitter:      2020-12-18T20:08:51
    # youtube:      2020-11-10T04:54:51Z
    def normalize_datetime(self, time_posted):
        if self.social_media != 'instagram':
            # split into date and time components
            date_time = time_posted.split('T')
            if self.social_media != 'twitter':
                date_time[1] = date_time[1][:(date_time[1].index('Z') if '.' not in date_time[1] else date_time[1].index('.'))]
            return ' '.join(date_time)
        return time_posted
