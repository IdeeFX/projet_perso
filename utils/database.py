import logging
import os
from datetime import timedelta, datetime
from shutil import copy
from distutils.util import strtobool
from tempfile import gettempdir
from settings.settings_manager import SettingsManager
from flask_sqlalchemy import SQLAlchemy
from utils.const import REQ_STATUS, RANDOM_ID_LENGTH, REFRESH_DATABASE_LIMIT

try:
    DEBUG = bool(strtobool(os.environ.get("MFSERV_HARNESS_DEBUG") or "False"))
except ValueError:
    DEBUG = False
LOGGER = logging.getLogger(__name__)

DTB = SQLAlchemy()


class Database():

    _app = None
    _dtb = None
    _db_file = None
    _last_refresh = None

    @classmethod
    def initialize_database(cls, app=None):
    # def initialize_database(cls, app):
        cls._app = app
        if DEBUG:
            db_dir = os.path.join(gettempdir(), "harnais")
        else:
            db_dir = SettingsManager.get("harnaisDir")
        db_file = os.path.join(db_dir, "harnais.database")
        # if a database has already been set, we keep it

        if cls._db_file is not None and cls._db_file!=db_file:
            copy(cls._db_file, db_file)
        cls._db_file = db_file

        uri = 'sqlite:///{db_file}'.format(db_file=db_file)
        app.config['SQLALCHEMY_DATABASE_URI'] = uri
        LOGGER.info("Flask app database uri set up to %s", uri)
        cls._dtb = DTB
        # connect the database to the app
        # see http://flask-sqlalchemy.pocoo.org/2.3/contexts/ for the use of app_context
        with app.app_context():
            DTB.init_app(app)
            DTB.create_all()

        # check if a refresh is necessary
        limit = timedelta(**REFRESH_DATABASE_LIMIT)
        if cls._last_refresh is None or (datetime.now() - last_refresh) > limit:
            cls.refresh(**REFRESH_DATABASE_LIMIT)

    @classmethod
    def get_database(cls):
        return cls._dtb

    @classmethod
    def get_app(cls):
        if DEBUG:
            db_dir = os.path.join(gettempdir(), "harnais")
        else:
            db_dir = SettingsManager.get("harnaisDir")
        db_file = os.path.join(db_dir, "harnais.database")

        if db_file != cls._db_file and cls._db_file is not None:
            from webservice.server.application import APP
            LOGGER.warning("Database file path was changed, "
                           "reinitialisation of the database.")
            cls.initialize_database(APP)

        return cls._app

    @classmethod
    def update_field_by_query(cls, fieldname, value, **kwargs):

        # TODO refresh is only performed for this query. Look into making
        # it a decorator
        # check if a refresh is necessary
        limit = timedelta(**REFRESH_DATABASE_LIMIT)
        if cls._last_refresh is None or (datetime.now() - last_refresh) > limit:
            cls.refresh(**REFRESH_DATABASE_LIMIT)


        # records = session.query(Diffusion).filter(Diffusion.fullrequestId = req_id + hostname).all()
        with cls.get_app().app_context():
            records = Diffusion.query.filter_by(**kwargs).all()

            for rec in records:
                setattr(rec, fieldname, value)

            cls._dtb.session.commit()


    @classmethod
    def get_request_status(cls,req_id):

        with cls.get_app().app_context():
            records = Diffusion.query.filter(Diffusion.fullrequestId.contains(req_id)).all()

        # if list is empty, no records
        if records == []:
            LOGGER.warning("Requesting status for non existing request "
                           "Id %s in database.", req_id)
            return REQ_STATUS.failed

        status = records[0].requestStatus
        #check that all records are the same
        for rec in records[1:]:
            if status != rec.requestStatus:
                LOGGER.error("Records with same fullrequestId have "
                             "different requestStatus. This should NEVER "
                             "happen !")
        return status

    @classmethod
    def get_creation_date(cls, req_id):
        with cls.get_app().app_context():
            return Diffusion.query.filter_by(fullrequestId=req_id).first().Date

    @classmethod
    def get_external_id(cls, req_id):
        with cls.get_app().app_context():
            return Diffusion.query.filter_by(fullrequestId=req_id).first().diff_externalid

    @classmethod
    def get_id_list_by_filename(cls, filename):

        with cls.get_app().app_context():
            records = Diffusion.query.filter_by(original_file=filename).all()
        id_list = []
        for rec in records:
            if rec.fullrequestId not in id_list:
                id_list.append(rec.fullrequestId)

        return id_list

    @classmethod
    def get_id_by_query(cls, **kwargs):

        # records = session.query(Diffusion).filter(Diffusion.fullrequestId = req_id + hostname).all()
        # TODO test if none
        with cls.get_app().app_context():
            record = Diffusion.query.filter_by(**kwargs).first()

        return record.fullrequestId


    @classmethod
    def get_diss_status(cls, req_id):

        with cls.get_app().app_context():
            status = cls.get_request_status(req_id)

            message = Diffusion.query.filter(Diffusion.fullrequestId.\
                      contains(req_id)).first().message or ""

        return status, message

    @classmethod
    def refresh(cls, **kwargs):
        with cls.get_app().app_context():
            records = Diffusion.query.filter(Diffusion.Date < datetime.now() - timedelta(**kwargs)).all()

            for rec in records:
                cls._dtb.session.delete(rec)
                LOGGER.debug("Deleted record %s aged over %s",
                             rec,
                             kwargs)

            if len(records) !=0:
                msg_dict = dict(days=0,seconds=0)
                msg_dict.update(kwargs)
                msg = "{days} days {seconds} seconds".format(**msg_dict)
                cls._dtb.session.commit()
                LOGGER.info("Deleted %i records aged over %s",
                            len(records),
                            msg)
        _last_refresh = datetime.now()



class Diffusion(DTB.Model):

    status_values = (REQ_STATUS.ongoing, REQ_STATUS.failed, REQ_STATUS.succeeded)

    diff_externalid = DTB.Column(DTB.String(
        RANDOM_ID_LENGTH), nullable=False, primary_key=True)
    fullrequestId = DTB.Column(DTB.String, nullable=False)
    original_file = DTB.Column(DTB.String)
    final_file = DTB.Column(DTB.String)
    requestStatus = DTB.Column(DTB.Enum(*status_values), nullable=False)
    message = DTB.Column(DTB.String)
    Date = DTB.Column(DTB.DateTime, nullable=False)
    rxnotif = DTB.Column(DTB.Boolean, nullable=False)

    def __repr__(self):
        repr_ = ('<Diffusion(diff_externalid={diff_externalid}, '
                 'fullrequestId={fullrequestId}, '
                 'original_file={original_file}, '
                 'final_file={final_file}, '
                 'status_values={status_values}, '
                 'requestStatus={requestStatus}, '
                 'message={message}, '
                 'Date={Date}, '
                 'rxnotif={rxnotif}, '
                 ')>'.format(**self.__dict__))

        return repr_
