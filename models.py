import os
from sqlalchemy import Column, String, Integer,create_engine
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2.types import Geometry
from shapely.geometry import Point
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_DWithin
from geoalchemy2.types import Geography
from sqlalchemy.sql.expression import cast
from geoalchemy2.shape import from_shape
from flask_login import UserMixin

db = SQLAlchemy()

'''
setup_db(app):
    binds a flask application and a SQLAlchemy service
'''
def setup_db(app):
    database_path = os.getenv('DATABASE_URL', 'DATABASE_URL_WAS_NOT_SET?!')

    # https://stackoverflow.com/questions/62688256/sqlalchemy-exc-nosuchmoduleerror-cant-load-plugin-sqlalchemy-dialectspostgre
    database_path = database_path.replace('postgres://', 'postgresql://')

    app.config["SQLALCHEMY_DATABASE_URI"] = database_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.app = app
    db.init_app(app)

'''
    drops the database tables and starts fresh
    can be used to initialize a clean database 
'''

def db_drop_and_create_all():
    db.drop_all()
    db.create_all()

    # Initial sample data:
    insert_sample_locations()

def insert_sample_locations():
    loc1 = SampleLocation(
        description='Osterbrook 5',
        geom=SampleLocation.point_representation(
            latitude=53.550552, 
            longitude=10.057432
        )
    )
    loc1.insert()

    loc2 = SampleLocation(
        description='Schadesweg 10',
        geom=SampleLocation.point_representation(
            latitude=53.546873, 
            longitude=10.05178
        )
    )
    loc2.insert()

    loc3 = SampleLocation(
        description='Bei der Hammer Kirche 3',
        geom=SampleLocation.point_representation(
            latitude=49.852851, 
            longitude=12.109204
        )
    )
    loc3.insert()

class SpatialConstants:
    SRID = 4326
    @staticmethod
    def point_representation(latitude, longitude):
        point = 'POINT(%s %s)' % (longitude, latitude)
        wkb_element = WKTElement(point, srid=SpatialConstants.SRID)
        return wkb_element
    @staticmethod
    def get_location_latitude(geom):
        point = to_shape(geom)
        return point.y
    @staticmethod
    def get_location_longitude(geom):
        point = to_shape(geom)
        return point.x

class SampleLocation(db.Model):
    __tablename__ = 'sample_locations'

    id = Column(Integer, primary_key=True)
    description = Column(String(80))
    geom = Column(Geometry(geometry_type='POINT', srid=SpatialConstants.SRID))  

    @staticmethod
    def point_representation(latitude, longitude):
        point = 'POINT(%s %s)' % (longitude, latitude)
        wkb_element = WKTElement(point, srid=SpatialConstants.SRID)
        return wkb_element

    @staticmethod
    def get_items_within_radius(lat, lng, radius):
        """Return all sample locations within a given radius (in meters)"""

        #TODO: The arbitrary limit = 100 is just a quick way to make sure 
        # we won't return tons of entries at once, 
        # paging needs to be in place for real usecase
        results = SampleLocation.query.filter(
            ST_DWithin(
                cast(SampleLocation.geom, Geography),
                cast(from_shape(Point(lng, lat)), Geography),
                radius)
            ).limit(100).all() 

        return [l.to_dict() for l in results]    

    def get_location_latitude(self):
        point = to_shape(self.geom)
        return point.y

    def get_location_longitude(self):
        point = to_shape(self.geom)
        return point.x  

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'location': {
                'lng': self.get_location_longitude(),
                'lat': self.get_location_latitude()
            }
        }

    # Fetching nearest users profile

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def update(self):
        db.session.commit()  

# My project App user Model  

class AppUser(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(10), nullable=False)
    lastname = db.Column(db.String(10), nullable=False)
    lookup_address = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    profile_pic = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    fluent_languages = db.Column(db.String(200), nullable=False)
    other_languages = db.Column(db.String(200), nullable=False)
    interests = db.Column(db.Text, nullable=False)
    geom = db.Column(Geometry(geometry_type='POINT', srid=SpatialConstants.SRID))

    def __repr__(self):
        return f"AppUser('{self.firstname}', '{self.lastname}', '{self.lookup_address}, \
             '{self.fluent_languages}', '{self.other_languages}','{self.profile_pic}', '{self.interests}')"

    def to_dict(self):
        return {
            'id': self.id,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'profile_pic':self.profile_pic,
            'fluent_languages': self.fluent_languages,
            'other_languages': self.other_languages,
            'interests':self.interests,
            'location': {
                'lng': SpatialConstants.get_location_longitude(self.geom),
                'lat': SpatialConstants.get_location_latitude(self.geom)
            }
        }  

    @staticmethod
    def get_items_within_radius(lat, lng, radius):
        """Return all sample locations within a given radius (in meters)"""

        #TODO: The arbitrary limit = 100 is just a quick way to make sure 
        # we won't return tons of entries at once, 
        # paging needs to be in place for real usecase
        results = AppUser.query.filter(
            ST_DWithin(
                cast(AppUser.geom, Geography),
                cast(from_shape(Point(lng, lat)), Geography),
                radius)
            ).limit(100).all() 

        return [l.to_dict() for l in results]  