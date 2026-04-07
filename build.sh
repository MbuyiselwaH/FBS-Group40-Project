#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

export FLASK_APP=app:app

# Initialize migrations folder if it doesn't exist yet
if [ ! -d "migrations" ]; then
    flask db init
fi

# Generate migration from current models and apply
flask db migrate -m "auto migration" 2>/dev/null || true
flask db upgrade

# Seed default admin and facilities if needed
python -c "
from app import app, db

with app.app_context():
    from models import User, Facility

    if not User.query.filter_by(role='admin').first():
        admin = User(
            student_number='ADMIN001',
            name='System',
            surname='Administrator',
            email='hadebema69@gmail.com',
            role='admin',
        )
        admin.set_password('Admin@1234')
        db.session.add(admin)
        db.session.commit()
        print('Default admin created.')
    else:
        print('Admin already exists.')

    if Facility.query.count() == 0:
        facilities = [
            Facility(name='Computer Lab A', facility_type='lab', campus='Steve Biko',
                     location='Block A, Room 101', capacity=30,
                     description='Modern computer lab with 30 workstations.',
                     equipment='30 PCs, Projector, Whiteboard, WiFi'),
            Facility(name='Computer Lab B', facility_type='lab', campus='ML Sultan',
                     location='Block A, Room 102', capacity=25,
                     description='Programming lab with Linux and Windows systems.',
                     equipment='25 PCs, Dual Monitors, Network Switch'),
            Facility(name='Main Hall', facility_type='hall', campus='Steve Biko',
                     location='Admin Block, Ground Floor', capacity=300,
                     description='Large multipurpose hall for events.',
                     equipment='PA System, Projector, Stage, Chairs'),
            Facility(name='Seminar Room 1', facility_type='hall', campus='Ritson',
                     location='Block B, Room 201', capacity=50,
                     description='Ideal for seminars and group presentations.',
                     equipment='Projector, Whiteboard, Conference Table'),
            Facility(name='Sports Hall', facility_type='sports', campus='Indumiso',
                     location='Sports Complex', capacity=100,
                     description='Indoor sports hall.',
                     equipment='Basketball Hoops, Volleyball Net, Scoreboards'),
            Facility(name='Soccer Field', facility_type='sports', campus='Riverside',
                     location='Sports Grounds', capacity=200,
                     description='Full-size soccer field with floodlights.',
                     equipment='Goalposts, Floodlights, Changing Rooms'),
            Facility(name='Lecture Hall 1', facility_type='lecture_room', campus='City Campus',
                     location='Block C, Room 001', capacity=120,
                     description='Large tiered lecture theatre.',
                     equipment='Projector, Microphone, Recording System'),
        ]
        for f in facilities:
            db.session.add(f)
        db.session.commit()
        print(f'{len(facilities)} facilities seeded.')
    else:
        print('Facilities already exist.')
"
