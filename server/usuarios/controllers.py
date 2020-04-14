from .models import *
from tornado.gen import coroutine
from .managers import *
from ..common.controllers import CrudController, SuperController
import json
import requests
import os.path
import dropbox
global api
import uuid

class UsuarioController(CrudController):
    manager = UsuarioManager
    html_index = "usuarios/views/usuario/index.html"
    html_table = "usuarios/views/usuario/table.html"
    routes = {
        '/usuario': {'GET': 'index', 'POST': 'table'},
        '/usuario_insert': {'POST': 'insert'},
        '/usuario_update': {'PUT': 'edit', 'POST': 'update'},
        '/usuario_delete': {'POST': 'delete_user'}
    }

    def index(self):
        self.set_session()
        self.verif_privileges()
        result = self.manager(self.db).list_all()
        result['privileges'] = UsuarioManager(self.db).get_privileges(self.get_user_id(), self.request.uri)
        result.update(self.get_extra_data())
        self.render(self.html_index, **result)
        self.db.close()

    def get_extra_data(self):
        aux = super().get_extra_data()
        aux['roles'] = RolManager(self.db).get_all()
        return aux

    def insert(self):
      self.set_session()
      try:
        diccionary = json.loads(self.get_argument("object"))
        diccionary['user_id'] = self.get_user_id()
        if "archivo" in self.request.files:
          cliente = dropbox.Dropbox('cLmD-0p1dtAAAAAAAAAAHeDultc8bjzmfdHNMPOCS4h8WPXAOKYIBj395iED2Ect')
          fileinfo = self.request.files["archivo"][0]
          fname = fileinfo.filename
          extn = os.path.splitext(fname)[1]
          cname = str(uuid.uuid4()) + extn
          # CORRECCION DROPBOX
          respuesta = cliente.files_upload(fileinfo.body, '/images/' + cname)
          link = cliente.sharing_create_shared_link('/images/' + cname)
          ruta = str(link.url).replace("dl=0", "raw=1")
          diccionary['foto'] = ruta
        else:
          link = ' '
          diccionary['portada'] = link
        objeto = self.manager(self.db).entity(**diccionary)
        UsuarioManager(self.db).insert(objeto)
        self.respond(success=True, message='Insertado correctamente.')
      except Exception as e:
        self.respond(success=False, message='Ocurrio un problema al insertar.')
        print(e)
      self.db.close()

    def update(self):
        self.set_session()
        diccionary = json.loads(self.get_argument("object"))
        diccionary['user_id'] = self.get_user_id()
        if "archivo" in self.request.files:
          cliente = dropbox.Dropbox('v0XIGaIghHAAAAAAAAADAgg3xp2eCberUJZWuuMgvE-908fJEAYi7EPWnSsfGECG')
          fileinfo = self.request.files["archivo"][0]
          fname = fileinfo.filename
          extn = os.path.splitext(fname)[1]
          cname = str(uuid.uuid4()) + extn
          # CORRECCION DROPBOX
          respuesta = cliente.files_upload(fileinfo.body, '/images/' + cname)
          link = cliente.sharing_create_shared_link('/images/' + cname)
          ruta = str(link.url).replace("dl=0", "raw=1")
          diccionary['foto'] = ruta
        objeto = self.manager(self.db).entity(**diccionary)
        UsuarioManager(self.db).update(objeto)
        self.respond(success=True, message='Modificado correctamente.')
        self.db.close()

    def delete_user(self):
        self.set_session()
        ins_manager = self.manager(self.db)
        diccionary = json.loads(self.get_argument("objeto"))
        id = diccionary['id']
        enable = diccionary['enabled']
        resp = UsuarioManager(self.db).delete_user(id, enable, self.get_user_id(), self.request.remote_ip)
        if resp:
            if enable == True:
                msg = 'Usuario activado correctamente.'
            else:
                msg = 'Usuario eliminado correctamente.'
            self.respond(success=True, message=msg)
        else:
            msg = 'Rol asignado dado de baja, no es posible habilitar el usuario.'
            self.respond(success=False, message=msg)

class RolController(CrudController):
    manager = RolManager
    html_index = "usuarios/views/rol/index.html"
    html_table = "usuarios/views/rol/table.html"
    routes = {
        '/rol': {'GET': 'index', 'POST': 'table'},
        '/rol_insert': {'POST': 'insert'},
        '/rol_update': {'PUT': 'edit', 'POST': 'update'},
        '/rol_delete': {'POST': 'delete_rol'}
    }

    def get_extra_data(self):
        aux = super().get_extra_data()
        aux['modulos'] = ModuloManager(self.db).list_all()
        return aux

    def insert(self):
        self.set_session()
        diccionary = json.loads(self.get_argument("object"))
        diccionary['user'] = self.get_user_id()
        diccionary['ip'] = self.request.remote_ip
        objeto = self.manager(self.db).entity(**diccionary)
        RolManager(self.db).insert(objeto)
        self.respond(success=True, message='Insertado correctamente.')

    def update(self):
        self.set_session()
        diccionary = json.loads(self.get_argument("object"))
        diccionary['user'] = self.get_user_id()
        diccionary['ip'] = self.request.remote_ip
        objeto = self.manager(self.db).entity(**diccionary)
        RolManager(self.db).update(objeto)
        self.respond(success=True, message='Modificado correctamente.')

    def delete_rol(self):
        self.set_session()
        ins_manager = self.manager(self.db)
        diccionary = json.loads(self.get_argument("object"))
        id = diccionary['id']
        enable = diccionary['enabled']

        RolManager(self.db).delete_rol(id, enable, self.get_user_id(), self.request.remote_ip)
        if enable == True:
            msg = 'Rol activado correctamente.'
        else:
            msg = 'Rol inhabilitado correctamente.'
        self.respond(success=True, message=msg)


class LoginController(SuperController):
    @coroutine
    def get(self):
        """Renderiza el login"""
        self.set_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.set_header('Pragma', 'no-cache')
        self.set_header('Expires', '0')
        usuario = self.get_secure_cookie("user")
        if usuario:
            self.redirect("/")
        else:
            self.clear_cookie("user")
            self.render("usuarios/views/login/index.html", error=0)

    @coroutine
    def post(self):
        """Inicia sesión en la aplicación.

        Si se inicia sesión con éxito enctonces se guarda el
        usuario en la cookie caso contrario se vuelve al login.
        """
        self.check_xsrf_cookie()
        ip = self.request.remote_ip
        username = self.get_argument('username', default=None)
        password = self.get_argument('password', default=None)

        if username is not None and password is not None:
            user = LoginManager().login(username, password)
            if user:
                self.set_user_id(user.id)
                self.redirect("/")
            else:
                userb = LoginManager().not_enabled(username, password)
                if userb:
                    self.render("usuarios/views/login/index.html", error=1)
                else:
                    self.render("usuarios/views/login/index.html", error=2)
        else:
            self.render("usuarios/views/login/index.html", error=2)

class LogoutController(SuperController):
    @coroutine
    def get(self):
        try:
            user_id = self.get_user_id()
            ip = self.request.remote_ip
            self.clear_cookie('user')
            self.redirect(self.get_argument("next", "/"))
        except Exception as e:
            self.clear_cookie('user')
            self.redirect(self.get_argument("next", "/"))

