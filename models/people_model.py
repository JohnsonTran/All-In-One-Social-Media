from app import db

class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500))
    instagram = db.Column(db.String(500))
    twitter = db.Column(db.String(500))
    youtube = db.Column(db.String(500))
    youtube_id = db.Column(db.String(500))

    def as_dict(self):
        return {'name': self.name}