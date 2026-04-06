#Run this script once to create all database tables and seed initial data.
from app import app, db


def seed_admin():
    from models import User
    if User.query.filter_by(role='admin').first():
        return
    admin = User(
        student_number = 'ADMIN001',
        name           = 'System',
        surname        = 'Administrator',
        email          = 'hadebema69@gmail.com',
        role           = 'admin',
    )
    admin.set_password('Admin@1234')
    db.session.add(admin)
    print('  Admin user created.')


def seed_facilities():
    from models import Facility
    if Facility.query.count() > 0:
        return
    facilities = [
        Facility(
            name          = 'Computer Lab A',
            facility_type = 'lab',
            campus        = 'Steve Biko',
            location      = 'Block A, Room 101',
            capacity      = 30,
            description   = 'Modern computer lab with 30 workstations.',
            equipment     = '30 PCs, Projector, Whiteboard, WiFi',
        ),
        Facility(
            name          = 'Computer Lab B',
            facility_type = 'lab',
            campus        = 'ML Sultan',
            location      = 'Block A, Room 102',
            capacity      = 25,
            description   = 'Programming lab with Linux and Windows systems.',
            equipment     = '25 PCs, Dual Monitors, Network Switch',
        ),
        Facility(
            name          = 'Main Hall',
            facility_type = 'hall',
            campus        = 'Steve Biko',
            location      = 'Admin Block, Ground Floor',
            capacity      = 300,
            description   = 'Large multipurpose hall for events.',
            equipment     = 'PA System, Projector, Stage, Chairs',
        ),
        Facility(
            name          = 'Seminar Room 1',
            facility_type = 'hall',
            campus        = 'Ritson',
            location      = 'Block B, Room 201',
            capacity      = 50,
            description   = 'Ideal for seminars and group presentations.',
            equipment     = 'Projector, Whiteboard, Conference Table',
        ),
        Facility(
            name          = 'Sports Hall',
            facility_type = 'sports',
            campus        = 'Indumiso',
            location      = 'Sports Complex',
            capacity      = 100,
            description   = 'Indoor sports hall.',
            equipment     = 'Basketball Hoops, Volleyball Net, Scoreboards',
        ),
        Facility(
            name          = 'Soccer Field',
            facility_type = 'sports',
            campus        = 'Riverside',
            location      = 'Sports Grounds',
            capacity      = 200,
            description   = 'Full-size soccer field with floodlights.',
            equipment     = 'Goalposts, Floodlights, Changing Rooms',
        ),
        Facility(
            name          = 'Lecture Hall 1',
            facility_type = 'lecture_room',
            campus        = 'City Campus',
            location      = 'Block C, Room 001',
            capacity      = 120,
            description   = 'Large tiered lecture theatre.',
            equipment     = 'Projector, Microphone, Recording System',
        ),
    ]
    for f in facilities:
        db.session.add(f)
    print(f'  {len(facilities)} facilities seeded.')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('Database tables created.')
        seed_admin()
        seed_facilities()
        db.session.commit()
        print('Done.')
