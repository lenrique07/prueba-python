import hashlib
import string
import random
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.session import make_transient
from ..database.connection import transaction
from server.common.managers import SuperManager, Error
from .models import *
from sqlalchemy.sql import func
from random import *

class UsuarioManager(SuperManager):
    def __init__(self, db):
        super().__init__(Usuario, db)

    def list_all(self):
        return dict(objects=self.db.query(Usuario).filter(Usuario.id != 1).distinct())

    def get_privileges(self, id, route):
        parent_module = self.db.query(Modulo).join(Rol.modulos).join(Usuario).filter(Modulo.route == route).filter(Usuario.id == id).filter(Usuario.enabled).first()
        if not parent_module:
            return dict()
        modules = self.db.query(Modulo).join(Rol.modulos).join(Usuario).filter(Modulo.fkmodulo == parent_module.id).filter(Usuario.id == id).filter(Usuario.enabled)
        privileges = {parent_module.name: parent_module}
        for module in modules:
            privileges[module.name] = module
        return privileges

    def insert(self, Usuario):
        if Usuario.fkrol > 0:
            Usuario.password = hashlib.sha512(Usuario.password.encode()).hexdigest()
            codigo = self.get_random_string()
            Usuario.codigo = codigo
            u = super().insert(Usuario)
            return u
        return Error('unknown')

    def update(self, Usuarioupd):
        Usuarioupd.password = hashlib.sha512(Usuarioupd.password.encode()).hexdigest()
        user = self.db.query(Usuario).filter(Usuario.id == Usuarioupd.id).one()
        return super().update(Usuarioupd)

    def delete_user(self, id, enable, Usuariocr, ip):
        x = self.db.query(Usuario).filter(Usuario.id == id).one()
        if enable == True:
            r = self.db.query(Rol).filter(Rol.id == x.fkrol).one()
            if r.enabled:
                x.enabled = enable
            else:
                return False
            message = "Se habilitó un usuario."
        else:
            x.enabled = enable
            message = "Se inhabilitó un usuario."
        self.db.merge(x)
        self.db.commit()
        return True

    def get_random_string(self):
        random_list = []
        for i in range(8):
            random_list.append(random.choice(string.ascii_uppercase + string.digits))
        return ''.join(random_list)

    def has_access(self, id, route):
        aux = self.db.query(Usuario.id).\
            join(Rol).join(Acceso).join(Modulo).\
            filter(Usuario.id == id).\
            filter(Modulo.route == route).\
            filter(Usuario.enabled).\
            all()
        return len(aux) != 0

    def get_page(self, page_nr=1, max_entries=10, like_search=None, order_by=None, ascendant=True, query=None):
        query = self.db.query(Usuario).join(Rol).filter(Rol.id > 1)
        return super().get_page(page_nr, max_entries, like_search, order_by, ascendant, query)

    def login_Usuario(self, username, password):
        password = hashlib.sha512(password.encode()).hexdigest()
        return self.db.query(Usuario).filter(Usuario.username == username).filter(Usuario.password == password).filter(
            Usuario.enabled == 1)

    def get_userById(self, id):
        return dict(profile=self.db.query(Usuario).filter(Usuario.id == id).first())


    def get_by_pass(self, Usuario_id):
        return self.db.query(Usuario).filter(Usuario.id == Usuario_id).first()

    def validar_usuario(self, username, password):
        password = hashlib.sha512(password.encode()).hexdigest()
        return self.db.query(func.count(Usuario.id)).filter(Usuario.username == username).filter(
            Usuario.enabled == True).filter(Usuario.password == password).scalar()

    def validar_usuario_sesion(self, codigo, usuario):
        return self.db.query(func.count(Usuario.id)).filter(Usuario.codigo == codigo).filter(
            Usuario.enabled == True).filter(Usuario.id == usuario).scalar()

    def activate_Usuario(self, usuario):
        usuario = self.db.query(Usuario).filter_by(id=usuario).first()
        usuario.activo = 1
        self.db.merge(usuario)
        self.db.commit()

    def listar_todo(self, id):
        return self.db.query(Usuario).filter(Usuario.enabled == True).filter(Usuario.id == id)

class RolManager(SuperManager):
    def __init__(self, db):
        super().__init__(Rol, db)

    def get_all(self):
        return self.db.query(Rol).filter(Rol.enabled == True).filter(Rol.id != 1)

    def get_page(self, page_nr=1, max_entries=10, like_search=None, order_by=None, ascendant=True, query=None):
        query = self.db.query(self.entity).filter(Rol.id > 1)
        return super().get_page(page_nr, max_entries, like_search, order_by, ascendant, query)

    def insert(self, rol):
        a = super().insert(rol)
        return a

    def update(self, rol):
        a = super().update(rol)
        return a

    def list_all(self):
        return dict(objects=self.db.query(Rol).filter(Rol.id != 1 ).distinct())



    def delete_rol(self, id, enable, Usuariocr, ip):
        x = self.db.query(Rol).filter(Rol.id == id).one()
        x.enabled = enable

        if enable == True:
            message = "Se habilitó un rol."
        else:
            users = self.db.query(Usuario).filter(Usuario.enabled == True).filter(Usuario.fkrol == id).all()
            for u in users:
                u.enabled = False
            message = "Se inhabilitó un rol y usuarios relacionados."
        self.db.merge(x)
        self.db.commit()


class ModuloManager:
    def __init__(self, db):
        self.db = db

    def list_all(self):
        return self.db.query(Modulo).filter(Modulo.fkmodulo==None)
class LoginManager:

    def login(self, username, password):
        """Retorna un usuario que coincida con el username y password dados.

        parameters
        ----------
        Usuarioname : str
        password : str
            El password deberá estar sin encriptar.

        returns
        -------
        Usuario
        None
            Retornará None si no encuentra nada.
        """
        password = hashlib.sha512(password.encode()).hexdigest()
        with transaction() as session:
            usuario = session.query(Usuario).\
                options(joinedload('rol').
                        joinedload('modulos').
                        joinedload('children')).\
                filter(Usuario.username == username).\
                filter(Usuario.password == password).\
                filter(Usuario.enabled).\
                first()
            if not usuario:
                return None
            session.expunge(usuario)
            make_transient(usuario)
        usuario.rol.modulos = self.order_modules(usuario.rol.modulos)
        return usuario



    def not_enabled(self, username, password):
        """Retorna un usuario que coincida con el username y password dados.

        parameters
        ----------
        Usuarioname : str
        password : str
            El password deberá estar sin encriptar.

        returns
        -------
        Usuario
        None
            Retornará None si no encuentra nada.
        """
        password = hashlib.sha512(password.encode()).hexdigest()
        with transaction() as session:
            usuario = session.query(Usuario).\
                options(joinedload('rol').
                        joinedload('modulos').
                        joinedload('children')).\
                filter(Usuario.username == username).\
                filter(Usuario.password == password).\
                filter(Usuario.enabled == False).\
                first()
            if not usuario:
                return None
            session.expunge(usuario)
            make_transient(usuario)
        usuario.rol.modulos = self.order_modules(usuario.rol.modulos)
        return usuario

    def get(self, key):
        with transaction() as session:
            usuario = session.query(Usuario).\
                options(joinedload('rol').
                        joinedload('modulos').
                        joinedload('children')).\
                filter(Usuario.id == key).\
                filter(Usuario.enabled).\
                first()
            if not usuario:
                return None
            session.expunge(usuario)
            make_transient(usuario)
        usuario.rol.modulos = self.order_modules(usuario.rol.modulos)
        return usuario

    def order_modules(self, modules):
        modules.sort(key=lambda x: x.id)
        mods_parents = []
        mods = {}
        while len(modules) > 0:
            module = modules.pop(0)
            module.children = []
            mods[module.id] = module
            parent_module = mods.get(module.fkmodulo, None)
            if parent_module:
                parent_module.children.append(module)
            else:
                mods_parents.append(module)
        return mods_parents
