from flask import Flask
from extensions import db, login_manager, migrate, csrf, mail
import config

app = Flask(__name__)
app.config.from_object(config)

db.init_app(app)
login_manager.init_app(app)
migrate.init_app(app, db)
csrf.init_app(app)
mail.init_app(app)

from routes.auth          import auth
from routes.main          import main
from routes.bookings      import bookings
from routes.facilities    import facilities
from routes.admin         import admin
from routes.notifications import notifications_bp
from routes.analytics     import analytics
from routes.cart          import cart
from routes.payments      import payments
from routes.checkin       import checkin

app.register_blueprint(auth)
app.register_blueprint(main)
app.register_blueprint(bookings)
app.register_blueprint(facilities)
app.register_blueprint(admin)
app.register_blueprint(notifications_bp)
app.register_blueprint(analytics)
app.register_blueprint(cart)
app.register_blueprint(payments)
app.register_blueprint(checkin)

app.jinja_env.globals['enumerate'] = enumerate

# Start background scheduler — guard against double-start in Werkzeug debug reloader
import os
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    from utils.scheduler import init_scheduler
    init_scheduler(app)

if __name__ == '__main__':
    app.run(debug=True)
