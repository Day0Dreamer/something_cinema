import c4d
from c4d import gui
from c4d import plugins
from c4d import bitmaps
from c4d.threading import C4DThread
import maxon
import redshift

import os
import sys
import re
import weakref
from pathlib import Path
import shutil
import array
import webbrowser
from fontTools import ttLib
from itertools import chain

from ctypes import pythonapi, c_void_p, py_object

scr_dir = os.path.dirname(os.path.realpath(__file__))
modules = os.path.join(scr_dir, "packages")
sys.path.insert(1, modules)

from transliterate import translit, get_available_language_codes
import fileseq
from fileseq import FileSeqException

COLOR_BG = c4d.COLOR_BG
COLOR_TRANS = c4d.COLOR_TRANS
COLOR_LINE0 = c4d.COLOR_SB_BG1
COLOR_LINE1 = c4d.COLOR_SB_BG2

COLOR_WHITE = c4d.COLOR_TEXTFOCUS
COLOR_TEXT = c4d.COLOR_TEXT
COLOR_GRAY = c4d.COLOR_TEXT_DISABLED
COLOR_RED = c4d.COLOR_SB_VISIBILITY_DOT_DISABLED
COLOR_GREEN = c4d.COLOR_SB_VISIBILITY_DOT_ENABLED
COLOR_ORANGE = c4d.COLOR_TEXT_SELECTED

CACHE_INFO = {
    "Dynamics Body":   {
        "info":   c4d.RIGID_BODY_CACHE_MEMORY,
        "val":    "0 Byte",
        "enable": c4d.RIGID_BODY_CACHE_USE,
        "type":   "cache_rbd",
        "btn":    c4d.RIGID_BODY_CACHE_BAKE
    },
    "MoGraph Cache":   {
        "info":   c4d.MGCACHETAG_MEMORYUSED,
        "val":    "0 bytes",
        "enable": c4d.MGCACHETAG_ACTIVE,
        "type":   "cache_mograph",
        "btn":    c4d.MGCACHETAG_BAKESEQUENCE
    },
    "Cloth":           {
        "info":   c4d.CLOTH_CACHE_INFO2,
        "val":    "0 MBytes",
        "enable": c4d.CLOTH_BAKE,
        "type":   "cache_cloth",
        "btn":    c4d.CLOTH_DO_CALCULATE
    },
    "Spline Dynamics": {
        "info":   c4d.HAIR_SDYNAMICS_CACHE_INFO2,
        "val":    "0 B",
        "enable": c4d.HAIR_SDYNAMICS_CACHE_ENABLE,
        "type":   "cache_spline",
        "btn":    c4d.HAIR_SDYNAMICS_CACHE_CALCULATE
    },
    "Jiggle":          {
        "info":   c4d.ID_CA_JIGGLE_OBJECT_CACHE_INFO2,
        "val":    "0 B",
        "enable": c4d.ID_CA_JIGGLE_OBJECT_CACHE_ENABLE,
        "type":   "cache_jiggle",
        "btn":    c4d.ID_CA_JIGGLE_OBJECT_CACHE_CALCULATE
    },
    "Collision":       {
        "info":   c4d.ID_CA_COLLISION_DEFORMER_OBJECT_CACHE_INFO2,
        "val":    "0 B",
        "enable": c4d.ID_CA_COLLISION_DEFORMER_OBJECT_CACHE_ENABLE,
        "type":   "cache_collision",
        "btn":    c4d.ID_CA_COLLISION_DEFORMER_OBJECT_CACHE_CALCULATE
    },
    "Hair":            {
        "info":   c4d.HAIRSTYLE_DYNAMICS_CACHE_INFO2,
        "val":    "0 B",
        "enable": c4d.HAIRSTYLE_DYNAMICS_CACHE_ENABLE,
        "type":   "cache_hair",
        "btn":    c4d.HAIRSTYLE_DYNAMICS_CACHE_CALCULATE
    }
}

ROW_TXT = {
    "tex_char":          {
        "text":       "Asset {NAME} uses unacceptable characters or symbols.",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "tex_missing":       {
        "text":       "Texture is missing: {NAME}",
        "text_fixed": "Missed texture was found",
        "type":       "error",
        "btn":        [{
            "btn_type": "tex_relink",
            "text":     "relink",
            "weblink":  ""
        }, {
            "btn_type": "tex_clear",
            "text":     "clear",
            "weblink":  ""
        }, ]
    },
    "ren_fps":           {
        "text":       "Check FPS in Project Settings and Output Settings. FPS settings must be the same",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "ren_paths":         {
        "text":       "Output regular and multi-pass render paths are incorrect",
        "text_fixed": "Output paths were fixed",
        "type":       "error",
        "btn":        [{
            "btn_type": "fix_ren_paths",
            "text":     "fix"
        }],
        "btn_fixed":  []
    },
    "ren_takes":         {
        "text":       "Takes are used in this project. Mark the Takes you want to render. For more information, visit our website.",
        "text_fixed": "",
        "type":       "warning",
        "btn":        [{
            "btn_type": "web",
            "text":     "info",
            "weblink":  "http://lacrimasfarm.com"
        }]
    },
    "ren_nomultipass":   {
        "text":       "No path for multi-pass output. If you don't want to use it, disable the multi-pass to avoid saving extra files.",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "ren_bucketsize":    {
        "text":       "Redshift bucket size (256x256) is not optimal. For more information, visit our website.",
        "text_fixed": "",
        "type":       "warning",
        "btn":        [{
            "btn_type": "web",
            "text":     "info",
            "weblink":  "http://lacrimasfarm.com"
        }]
    },
    "ren_framerange":    {
        "text":       "The render output is setted as single frame. Check the frame range in render settings.",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "ren_framestep":     {
        "text":       "The frame step is not equal to 1.",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "ren_videooutput":   {
        "text":       "Video file is not valid as output format",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "asset_alembic":     {
        "text":       "Alembic file {OBJ} is missing",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "asset_rsproxy":     {
        "text":       "RS Proxy {OBJ} is missing",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "asset_vdb":         {
        "text":       "VDB {OBJ} is missing",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "asset_ies":         {
        "text":       "IES {OBJ} is missing",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "asset_mocache":     {
        "text":       "MoCache {OBJ} is missing",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "asset_gicache":     {
        "text":       "GI Cache {NAME} is missing",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "cache_mograph":     {
        "text":       "Tag {OBJ} is not cached",
        "text_fixed": "",
        "type":       "error",
        "btn":        [{
            "btn_type": "bake",
            "text":     "bake",
            "weblink":  ""
        }]
    },
    "cache_particles":   {
        "text":       "Particle emitter {OBJ} is not cached",
        "text_fixed": "",
        "type":       "error",
        "btn":        [{
            "btn_type": "bake",
            "text":     "bake",
            "weblink":  ""
        }]
    },
    "cache_camera":      {
        "text":       "Camera {OBJ} used in the project. In some cases it must be baked. For more information, visit our website.",
        "text_fixed": "",
        "type":       "warning",
        "btn":        []
    },
    "cache_cloth":       {
        "text":       "Cloth Tag {OBJ} is not  cached",
        "text_fixed": "Cloth Tag {OBJ} was successfully cached",
        "type":       "error",
        "btn":        [{
            "btn_type": "bake",
            "text":     "bake",
            "weblink":  ""
        }]
    },
    "cache_hair":        {
        "text":       "Hair Object {OBJ} is not cached",
        "text_fixed": "Hair Object {OBJ} was successfully cached",
        "type":       "error",
        "btn":        [{
            "btn_type": "bake",
            "text":     "bake",
            "weblink":  ""
        }]
    },
    "cache_spline":      {
        "text":       "Spline Dynamics Tag {OBJ} is not cached",
        "text_fixed": "Spline Dynamics Tag {OBJ} was successfully cached",
        "type":       "error",
        "btn":        [{
            "btn_type": "bake",
            "text":     "bake",
            "weblink":  ""
        }]
    },
    "cache_rbd":         {
        "text":       "Dynamics Body Tag {OBJ} is not cached",
        "text_fixed": "Dynamics Body Tag {OBJ} was successfully cached",
        "type":       "error",
        "btn":        [{
            "btn_type": "bake",
            "text":     "bake",
            "weblink":  ""
        }]
    },
    "cache_jiggle":      {
        "text":       "Jiggle Deformer {OBJ} is not cached",
        "text_fixed": "Jiggle Deformer {OBJ} was successfully cached",
        "type":       "error",
        "btn":        [{
            "btn_type": "bake",
            "text":     "bake",
            "weblink":  ""
        }]
    },
    "cache_collision":   {
        "text":       "Collision Deformer {OBJ} is not cached",
        "text_fixed": "Collision Deformer {OBJ} was successfully cached",
        "type":       "error",
        "btn":        [{
            "btn_type": "bake",
            "text":     "bake",
            "weblink":  ""
        }]
    },
    "cache_constraint":  {
        "text":       "Constraint tag {OBJ} is used in the project. In some cases it should be baked.",
        "text_fixed": "",
        "type":       "warning",
        "btn":        [{
            "btn_type": "web",
            "text":     "info",
            "weblink":  "http://lacrimasfarm.com"
        }]
    },
    "cache_xpresso":     {
        "text":       "Xpresso tag {OBJ} is used in project. In some cases it should be baked. For more information, visit our website.",
        "text_fixed": "",
        "type":       "warning",
        "btn":        []
    },
    "font_motext":       {
        "text":       "Make MoText {OBJ} editable if it's possible to avoid issues with font.Or save it to the font project folder",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "font_used":         {
        "text":       "{OBJ} uses the font {NAME}. Copy it to the project folder.",
        "text_fixed": "{NAME} font saved to folder.",
        "type":       "error",
        "btn":        [{
            "btn_type": "save",
            "text":     "save"
        }]
    },
    "plugin_used":       {
        "text":       "Save invormation about Cinema 4d version and plugins used in the project.",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "plugin_thirdparty": {
        "text":       "{OBJ} is a third-party plugin.",
        "text_fixed": "",
        "type":       "error",
        "btn":        []
    },
    "no_errors":         {
        "text":       "No errors found.",
        "text_fixed": "",
        "type":       "ok",
        "btn":        []
    }
}


def load_bitmap(path):
    path = os.path.join(os.path.dirname(__file__), path)
    bmp = c4d.bitmaps.BaseBitmap()
    if bmp.InitWith(path)[0] != c4d.IMAGERESULT_OK:
        bmp = None
    return bmp


PLUGIN_ID = 1058909
PLUGIN_NAME = 'LacrimasFarmUploader'
PLUGIN_INFO = 0
PLUGIN_ICON = load_bitmap('res/icons/A_white_flat_80%_100x100.png')
PLUGIN_HELP = ''

DEFAULT_PROJ_PATH = "C:\FarmCollect\MyProject"


class Resource:
    def __init__(self, path):
        self.__path = path
        self.__symbols = {}
        self.__read_c4d_symbols(self.path('c4d_symbols.h'))

    def __getattr__(self, name):
        return self.__symbols[name]

    def __read_c4d_symbols(self, symbols_path):
        with open(symbols_path, 'r') as f:
            regex = re.compile(r'^(?P<symbol>\w+)=?(?P<id>\d+)?,')
            previuos_id = -1
            for line in f.readlines():
                line = line.replace(' ', '')
                m = regex.match(line)
                if m:
                    symbols_id = int(m.group('id')) if m.group('id') else previuos_id + 1
                    previuos_id = symbols_id
                    self.__symbols[m.group('symbol')] = symbols_id

    def path(self, filename):
        return os.path.join(self.__path, filename)

    @staticmethod
    def name(resource_id, *args):
        return plugins.GeLoadString(resource_id, *args)


res_path = os.path.dirname(__file__)
if not os.path.isdir(os.path.join(res_path, 'res')):
    res_path = os.path.dirname(res_path)
res = Resource(os.path.join(res_path, 'res'))


class Utils():
    @staticmethod
    def get_source_doc():
        return c4d.documents.GetActiveDocument()

    @staticmethod
    def get_rd():
        document = Utils.get_source_doc()
        return document.GetActiveRenderData()

    @staticmethod
    def get_render_engine_name():
        rd = Utils.get_rd()
        engine_id = rd[c4d.RDATA_RENDERENGINE]

        if engine_id == 0:
            return "Standard"
        vp = c4d.plugins.FindPlugin(engine_id, c4d.PLUGINTYPE_VIDEOPOST)
        return vp.GetName() if vp else "Unknown Engine"

    @staticmethod
    def get_frame_range():
        rd = Utils.get_rd()
        document = Utils.get_source_doc()
        start = rd[c4d.RDATA_FRAMEFROM].GetFrame(document.GetFps())
        end = rd[c4d.RDATA_FRAMETO].GetFrame(document.GetFps())
        return start, end

    @staticmethod
    def get_render_res():
        rd = Utils.get_rd()
        res = str(int(rd[c4d.RDATA_XRES_VIRTUAL])) + ' X ' + str(int(rd[c4d.RDATA_YRES_VIRTUAL]))
        return res

    @staticmethod
    def get_proj_name():
        proj_name = str(Path(Utils.get_proj_path()).name)
        return proj_name

    @staticmethod
    def get_proj_path():
        proj_path = DEFAULT_PROJ_PATH
        data = c4d.plugins.GetWorldPluginData(PLUGIN_ID)
        if data:
            path = data.GetString(1009)
            if not path:
                data = c4d.BaseContainer()
                path = proj_path
                data.SetString(1009, path)
                c4d.plugins.SetWorldPluginData(PLUGIN_ID, data)
            else:
                proj_path = path
        return proj_path

    @staticmethod
    def mkdir(path):
        # if os.path.isfile(path):
        # os.unlink(path)
        try:
            if not os.path.exists(path.encode('utf-8')):
                print(u'MKDIR %s' % path)
                os.makedirs(path)
        except:
            print("Couldn't create dir:", path)
        if os.path.exists(path.encode('utf-8')):
            return True
        else:
            return False

    @staticmethod
    def copyfile(src, trg):
        if Utils.mkdir(trg):
            try:
                shutil.copy2(src, trg)
            except EnvironmentError:
                pass
            else:
                return True
        return False

    @staticmethod
    def iterate_hierarchy(op):
        while op:
            yield op
            if op.GetDown():
                op = op.GetDown()
                continue
            while not op.GetNext() and op.GetUp():
                op = op.GetUp()
            op = op.GetNext()

    @staticmethod
    def scroll_to(obj):
        source_doc = Utils.get_source_doc()
        if isinstance(obj, c4d.BaseTag):
            source_doc.SetActiveObject(obj.GetObject())
            c4d.CallCommand(100004769)
            obj.GetObject().DelBit(c4d.BIT_ACTIVE)
            source_doc.SetActiveTag(obj)
        else:
            source_doc.SetActiveObject(obj)
            c4d.CallCommand(100004769)
        c4d.EventAdd()

    @staticmethod
    def get_translit_name(name):
        translit_name = translit(name, 'ru', reversed=True)
        translit_name = re.sub(r"[^a-zA-Z0-9!_ ]", "", translit_name)
        translit_name = translit_name.replace(" ", "_")
        return (translit_name)

    @staticmethod
    def relink_asset(asset):
        path = c4d.storage.LoadDialog(type=c4d.FILESELECTTYPE_IMAGES,
                                      title='Locate path for: {ASSETNAME}'.format(
                                          ASSETNAME=asset["assetname"]),
                                      flags=c4d.FILESELECT_LOAD,
                                      force_suffix='', def_path='', def_file='')
        if path:
            src = Path(path)
            translit_name = Utils.get_translit_name(src.stem)
            source_doc = Utils.get_source_doc()
            trg = Path(source_doc.GetDocumentPath()) / "tex" / (translit_name + src.suffix)
            try:
                tex_folder = str(Path(source_doc.GetDocumentPath()) / "tex")

                if Utils.mkdir(tex_folder):
                    shutil.copy2(path, trg)
                    textureURL = maxon.Url(translit_name + src.suffix)
                    textureOwner = asset["owner"]
                    if textureOwner.GetType() == 1001101:  # Redshift Shader
                        textureOwner[
                            c4d.REDSHIFT_SHADER_TEXTURESAMPLER_TEX0, c4d.REDSHIFT_FILE_PATH] = textureURL.GetSystemPath()
                        return True
                    elif textureOwner.GetType() == 1036751:  # RS Dome Light / Redshift Light
                        textureOwner[c4d.REDSHIFT_LIGHT_DOME_TEX0, c4d.REDSHIFT_FILE_PATH] = textureURL.GetSystemPath()
                        return True
            except IOError as e:
                print("Unable to copy file. %s" % e)
        return False

    @staticmethod
    def save_proj_path(proj_path):
        data = c4d.BaseContainer()
        path = proj_path
        data.SetString(1009, path)
        c4d.plugins.SetWorldPluginData(PLUGIN_ID, data)
        return True

    @staticmethod
    def is_takes(checkMarked=False):
        document = Utils.get_source_doc()
        td = document.GetTakeData()
        mt = td.GetMainTake()
        cnt_marks = 0
        cnt_takes = 0
        for x in Utils.iterate_hierarchy(mt):
            if x.IsChecked():
                cnt_marks += 1
            cnt_takes += 1

        if checkMarked:
            if cnt_takes > 1 and cnt_marks == 0:
                return True
        else:
            if cnt_takes > 1:
                return True
        return False

    @staticmethod
    def save_changes():
        save_path = str(Path(Utils.get_proj_path()) / Utils.get_proj_name())
        if c4d.documents.SaveDocument(Utils.get_source_doc(), save_path, c4d.SAVEDOCUMENTFLAGS_NONE, c4d.FORMAT_C4DEXPORT):
            return True
        else:
            return False


class CollectScene():
    def _save_project_assets(self):
        proj_path = Utils.get_proj_path()
        print("collect_folder:", proj_path)
        saved = False
        if Utils.mkdir(proj_path):
            self.check_mocache_external(proj_path)  # THIS CODE FOR HACK ISSUE WITH COLLECTING EXTERNAL .MOG CACHE
            source_doc = Utils.get_source_doc()
            self.assets = []
            self.missing_assets = []
            saved = c4d.documents.SaveProject(source_doc, c4d.SAVEPROJECT_ASSETS |
                                              c4d.SAVEPROJECT_SCENEFILE |
                                              c4d.SAVEPROJECT_DONTFAILONMISSINGASSETS |
                                              c4d.SAVEPROJECT_PROGRESSALLOWED |
                                              c4d.SAVEPROJECT_DONTTOUCHDOCUMENT,
                                              proj_path, self.assets, self.missing_assets)
            source_doc.DoUndo()
        return saved

    def _load_doc(self):
        proj_path = Utils.get_proj_path()
        proj_name = Utils.get_proj_name()
        file_name_src = os.path.join(proj_path, proj_name + '.c4d')
        load_doc = c4d.documents.LoadFile(file_name_src)
        if load_doc:
            self.set_mocache_paths(False)

        return load_doc

    def set_mocache_paths(self, is_old=True):
        for hierarchy, old_path, new_path in self.mocache_paths:
            obj = self.__get_obj_by_hierarchy(hierarchy)
            for tag in obj.GetTags():
                if tag.GetTypeName() == "MoGraph Cache" and tag[c4d.MGCACHETAG_MODE] == 1 and tag[c4d.MGCACHETAG_ACTIVE]:
                    if is_old:
                        tag[c4d.MGCACHETAG_EXPORT_CACHEFILE] = old_path
                        tag[c4d.MGCACHETAG_IMPORT_CACHEFILE] = old_path
                    else:
                        tag[c4d.MGCACHETAG_EXPORT_CACHEFILE] = new_path
                        tag[c4d.MGCACHETAG_IMPORT_CACHEFILE] = new_path

                    tag[c4d.MGCACHETAG_ACTIVE] = 0  # trigger tag checkbox to load cache
                    tag[c4d.MGCACHETAG_ACTIVE] = 1
        c4d.EventAdd()

    def check_mocache_external(self, dirname):
        self.mocache_paths = []
        folders_names = []
        cache_paths = []
        source_doc = Utils.get_source_doc()
        source_doc.StartUndo()
        for x in Utils.iterate_hierarchy(source_doc.GetFirstObject()):
            for tag in x.GetTags():
                if tag.GetTypeName() == "MoGraph Cache" and tag[c4d.MGCACHETAG_MODE] == 1 and tag[c4d.MGCACHETAG_ACTIVE]:
                    source_doc.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL, tag)
                    old_cache_path = tag[c4d.MGCACHETAG_IMPORT_CACHEFILE]
                    tag[c4d.MGCACHETAG_IMPORT_CACHEFILE] = ""

                    if old_cache_path not in cache_paths:
                        folder_name = x.GetName()
                        if folder_name in folders_names:
                            i = 0
                            while str(folder_name + "_%s" % i) in folders_names:
                                i += 1
                            folder_name = str(folder_name + "_%s" % i)

                        cache_name = str(Path(old_cache_path).name)
                        new_cache_path = str(Path(dirname) / folder_name / cache_name)
                        collect = self.__collect_mocache(old_cache_path, str(Path(new_cache_path).parent))
                        if collect:
                            cache_paths.append(old_cache_path)
                    else:
                        old_paths = list(zip(*self.mocache_paths))[1]
                        index = old_paths.index(old_cache_path)
                        new_cache_path = self.mocache_paths[index][2]

                    hierarchy_str = self.__get_hierarchy(x)
                    folders_names.append(folder_name)
                    self.mocache_paths.append([hierarchy_str, old_cache_path, new_cache_path])
        source_doc.EndUndo()

    def __collect_mocache(self, src, trg):
        try:
            seq_path = fileseq.findSequenceOnDisk(src + '@@@@.mog', strictPadding=True)
            files = list(fileseq.FileSequence(seq_path))
            if Utils.mkdir(trg):
                for file in files:
                    shutil.copy2(file, trg)
                return True
        except FileSeqException as e:
            print(e)
        return False

    def __get_hierarchy(self, obj):
        hierarchy_str = ""
        prev = obj
        while obj:
            obj = obj.GetPred()
            if obj:
                hierarchy_str += "n"
            else:
                obj = prev.GetUp()
                if obj:
                    hierarchy_str += "d"
            prev = obj
        return hierarchy_str[::-1]

    def __get_obj_by_hierarchy(self, hierarchy_str):
        source_doc = Utils.get_source_doc()
        obj = source_doc.GetFirstObject()
        for f in hierarchy_str:
            if f == "n":
                obj = obj.GetNext()
            elif f == "d":
                obj = obj.GetDown()
        return obj

    def is_collected(self):
        source_doc = Utils.get_source_doc()
        path = Path(source_doc.GetDocumentPath(), source_doc.GetDocumentName())
        proj_path = Path(Utils.get_proj_path()) / str(Utils.get_proj_name() + '.c4d')
        if path == proj_path:
            return True
        else:
            return False


class CheckAndFix():
    def __init__(self, worker):
        self.dialog = worker.dialog


class CheckAndFixTextures(CheckAndFix):

    def check(self):
        self.__check_textures()

    def __check_textures(self):
        textures = list()
        source_doc = Utils.get_source_doc()
        c4d.documents.GetAllAssetsNew(source_doc, False, "", c4d.ASSETDATA_FLAG_TEXTURESONLY, textures)
        for t in textures:
            if t["exists"]:
                continue
                """textureOwner = t["owner"]
                print(textureOwner)
                textureURL = maxon.Url(t["filename"])
                textureSuffix =  textureURL.GetSuffix()
                textureURL.ClearSuffix()
                textureURL.SetName(textureURL.GetName() + "_replaced")
                textureURL.SetSuffix(textureSuffix)
                print(textureURL.GetSystemPath())
                textureOwner[c4d.REDSHIFT_SHADER_TEXTURESAMPLER_TEX0,c4d.REDSHIFT_FILE_PATH] = textureURL.GetSystemPath()"""
            else:
                textureOwner = t["owner"]
                if textureOwner.GetType() == 1001101:  # Redshift Shader
                    UaLog('tex_missing', dialog=self.dialog(), object=t)
                """elif textureOwner.GetType() == 1036751:  # RS Dome Light / Redshift Light
                    text = "Asset is missing: {NAME}".format(NAME=t["assetname"])
                    UaLog('assets', text, dialog=self.dialog, object=t)
                    continue
                elif textureOwner.GetType() == 1019337:  #  MoGraph Cache
                    text = "Asset is missing: {NAME}".format(NAME=t["assetname"])
                    UaLog('assets', text, dialog=self.dialog, object=t)
                    continue"""
                # textureOwner[c4d.REDSHIFT_SHADER_TEXTURESAMPLER_TEX0,c4d.REDSHIFT_FILE_PATH] = ""

    def fix_clear_texture(self, asset):
        textureOwner = asset["owner"]
        textureOwner[c4d.REDSHIFT_SHADER_TEXTURESAMPLER_TEX0, c4d.REDSHIFT_FILE_PATH] = ""

        return False


class CheckAndFixRenderSettings(CheckAndFix):
    def check(self):
        self.__check_output_name()
        self.__check_fps()
        self.__check_takes()
        self.__check_output_format()
        self.__check_bucket_size()
        self.__check_frame_step()
        self.__check_frame_range()
        self.__check_multipass_epmty_psd()

    def __check_fps(self):
        rd = Utils.get_rd()
        document = Utils.get_source_doc()
        doc_fps = int(document[c4d.DOCUMENT_FPS])
        render_fps = int(rd[c4d.RDATA_FRAMERATE])
        if doc_fps != render_fps:
            UaLog('ren_fps', dialog=self.dialog())

    def __check_output_name(self):
        rd = Utils.get_rd()
        if Utils.is_takes():
            output_path_regular = "./render/$prj/$take/$prj_take"
            output_path_mp = "./multipass/$prj/$take/$prj_take"
        else:
            output_path_regular = "./render/$prj"
            output_path_mp = "./multipass/$prj"

        reg_path = rd[c4d.RDATA_PATH]
        mp_path = rd[c4d.RDATA_MULTIPASS_FILENAME]

        if reg_path != output_path_regular or mp_path != output_path_mp:
            UaLog('ren_paths', dialog=self.dialog())

    def __check_takes(self):
        if Utils.is_takes(checkMarked=True):
            UaLog('ren_takes', dialog=self.dialog())

    def __check_output_format(self):
        rd = Utils.get_rd()
        format = rd[c4d.RDATA_FORMAT]
        formats = [1073794140, 1073773172, 1122, 1125, 1073794144]
        if format in formats:
            UaLog('ren_videooutput', dialog=self.dialog())

    def __check_bucket_size(self):
        rd = Utils.get_rd()
        vprs = redshift.FindAddVideoPost(rd, redshift.VPrsrenderer)
        bucket_size = int(vprs[c4d.REDSHIFT_RENDERER_BLOCK_SIZE])
        if bucket_size != 64:
            UaLog('ren_bucketsize', dialog=self.dialog())

    def __check_frame_step(self):
        rd = Utils.get_rd()
        framestep = int(rd[c4d.RDATA_FRAMESTEP])
        if framestep != 1:
            UaLog('ren_framestep', dialog=self.dialog())

    def __check_frame_range(self):
        start, end = Utils.get_frame_range()
        if start == end:
            UaLog('ren_framerange', dialog=self.dialog())

    def __check_multipass_epmty_psd(self):
        rd = Utils.get_rd()
        save_mp = rd[c4d.RDATA_MULTIPASS_ENABLE] and rd[c4d.RDATA_MULTIPASS_SAVEIMAGE]
        mp_path_empty = rd[c4d.RDATA_MULTIPASS_FILENAME] == ""
        if mp_path_empty and save_mp:
            UaLog('ren_nomultipass', dialog=self.dialog())

    def __fix_fps(self):
        pass

    def fix_output_name(self):
        rd = Utils.get_rd()
        if Utils.is_takes():
            rd[c4d.RDATA_PATH] = "./render/$prj/$take/$prj_take"
            rd[c4d.RDATA_MULTIPASS_FILENAME] = "./multipass/$prj/$take/$prj_take"
        else:
            rd[c4d.RDATA_PATH] = "./render/$prj"
            rd[c4d.RDATA_MULTIPASS_FILENAME] = "./multipass/$prj"
        c4d.EventAdd()

    def __fix_takes(self):
        pass

    def __fix_output_format(self):
        pass

    def __fix_bucket_size(self):
        pass

    def __fix_frame_step(self):
        pass

    def __fix_frame_range(self):
        pass

    def __fix_multipass_epmty_psd(self):
        pass


class CheckAndFixAssets(CheckAndFix):
    def check(self):
        self.__check_cached()
        # self.__check_irr_cache()

    def __check_irr_cache(self):
        document = doc
        rd = document.GetActiveRenderData()
        rd_bc = rd.GetData()
        rpd = {
            '_doc':   document,
            '_rData': rd,
            '_rBc':   rd_bc,
            '_frame': 0
        }

        vprs = redshift.FindAddVideoPost(rd, redshift.VPrsrenderer)
        gi_enabled = vprs[c4d.REDSHIFT_RENDERER_GI_ENABLED]

        if gi_enabled == 1:
            doc_path = doc.GetDocumentPath()
            gi_eng_1 = vprs[c4d.REDSHIFT_RENDERER_PRIMARY_GI_ENGINE]
            gi_eng_mode_1 = vprs[c4d.REDSHIFT_RENDERER_IRRADIANCE_CACHE_MODE]
            if gi_eng_1 == 3 and gi_eng_mode_1 == 1:
                cache_str = vprs[c4d.REDSHIFT_RENDERER_IRRADIANCE_CACHE_FILENAME]
                cache_str_token = c4d.modules.tokensystem.StringConvertTokens(cache_str, rpd)

                gi_file = Path(doc_path, cache_str_token)
                if not gi_file.is_file():
                    print(gi_file, "not exist")

            gi_eng_2 = vprs[c4d.REDSHIFT_RENDERER_SECONDARY_GI_ENGINE]
            gi_eng_mode_2 = vprs[c4d.REDSHIFT_RENDERER_IRRADIANCE_CACHE_MODE]
            if gi_eng_2 == 2 and gi_eng_mode_2 == 1:
                cache_str = vprs[c4d.REDSHIFT_RENDERER_IRRADIANCE_POINT_CLOUD_FILENAME]
                cache_str_token = c4d.modules.tokensystem.StringConvertTokens(cache_str, rpd)
                gi_file = Path(doc_path, cache_str_token)
                if not gi_file.is_file():
                    print(gi_file, "not exist")

        # pc_str = rd[c4d.REDSHIFT_RENDERER_IRRADIANCE_POINT_CLOUD_FILENAME]

    def __check_cached(self):
        source_doc = Utils.get_source_doc()
        doc_path = source_doc.GetDocumentPath()
        for x in Utils.iterate_hierarchy(source_doc.GetFirstObject()):
            typename = x.GetTypeName()
            if typename == "Alembic Generator":
                if x[c4d.ALEMBIC_PATH_STATE] == 0 or x[c4d.ALEMBIC_IDENT_STATE] == 0:
                    UaLog('asset_alembic', dialog=self.dialog(), object=x)
            elif typename == "Redshift Light" and x[c4d.REDSHIFT_LIGHT_TYPE] == 5:
                ies_str = x[c4d.REDSHIFT_LIGHT_IES_PROFILE, c4d.REDSHIFT_FILE_PATH]
                ies_file = Path(doc_path, ies_str)
                if not ies_file.is_file():
                    UaLog('asset_ies', dialog=self.dialog(), object=x)
            elif typename == "Redshift Volume":
                vdb_str = x[c4d.REDSHIFT_VOLUME_FILE, c4d.REDSHIFT_FILE_PATH]
                vdb_file = Path(doc_path, "tex", vdb_str)
                if not vdb_file.is_file():
                    UaLog('asset_vdb', dialog=self.dialog(), object=x)
                pass
            elif typename == "Redshift Proxy":
                rspr_str = x[c4d.REDSHIFT_PROXY_FILE, c4d.REDSHIFT_FILE_PATH]
                rspr_file = Path(doc_path, "tex", rspr_str)
                if not rspr_file.is_file():
                    UaLog('asset_rsproxy', dialog=self.dialog(), object=x)

            for tag in x.GetTags():
                # if not self.__is_cached(tag):
                pass


class CheckAndFixCache(CheckAndFix):

    def check(self):
        source_doc = Utils.get_source_doc()
        for x in Utils.iterate_hierarchy(source_doc.GetFirstObject()):
            typename = x.GetTypeName()
            if typename == "Emitter":
                self.__check_particles_cache(x)
            elif typename in ["Cloner", "Matrix", "Fracture", "Voronoi Fracture", "MoInstance", "MoText", "MoSpline"]:
                self.__check_mograph_cache(x)
            elif typename in ["Jiggle", "Collision", "Hair"]:
                self.__check_cache_by_type(x)
            else:
                for tag in x.GetTags():
                    tag_typename = tag.GetTypeName()
                    if tag_typename in ["Dynamics Body", "Cloth", "Spline Dynamics"]:
                        self.__check_cache_by_type(tag)
                    elif tag_typename == "XPresso":
                        pass
                    elif tag_typename == "Constraint":
                        pass

    def __check_mograph_cache(self, obj):
        baked = False
        for tag in obj.GetTags():
            if tag.GetTypeName() == "MoGraph Cache":
                baked = True
        if not baked:
            UaLog('cache_mograph', dialog=self.dialog(), object=obj)

    def __check_particles_cache(self, obj):
        baked = False
        for tag in obj.GetTags():
            if tag.GetTypeName() == "Bake Particle":
                baked = True
        if not baked:
            UaLog('cache_particles', dialog=self.dialog(), object=obj)

    def __check_cache_by_type(self, obj):
        baked = self.is_baked(obj)
        obj_type = obj.GetTypeName()
        if not baked:
            UaLog(CACHE_INFO[obj_type]["type"], dialog=self.dialog(), object=obj)

    def is_baked(self, obj):
        obj_type = obj.GetTypeName()
        if obj_type in CACHE_INFO:
            info = obj[CACHE_INFO[obj_type]["info"]]
            val = CACHE_INFO[obj_type]["val"]
            enable = obj[CACHE_INFO[obj_type]["enable"]]

            baked = info != val and enable
            print(obj_type, baked, info, val, enable)

        return baked

    def fix_bake(self, obj):
        source_doc = Utils.get_source_doc()
        if isinstance(obj, c4d.BaseTag):
            objs = source_doc.GetActiveTags()
            source_doc.SetActiveTag(obj)
        else:
            objs = source_doc.GetActiveObjects(flags=c4d.GETACTIVEOBJECTFLAGS_NONE)
            source_doc.SetActiveObject(obj)
        dc = {}
        dc['id'] = CACHE_INFO[obj.GetTypeName()]["btn"]
        obj.Message(c4d.MSG_DESCRIPTION_COMMAND, dc)
        obj[CACHE_INFO[obj.GetTypeName()]["enable"]] = True
        obj.DelBit(c4d.BIT_ACTIVE)
        for o in objs:
            o.SetBit(c4d.BIT_ACTIVE)
        if self.is_baked(obj):
            return True
        else:
            return False


class CheckAndFixFonts(CheckAndFix):
    def check(self):
        fonts_path = []

        win_dir = os.path.join(os.environ['WINDIR'], 'fonts')
        user_dir = Path.home() / "AppData/Local/Microsoft/Windows/Fonts"

        paths = (win_dir, user_dir)

        for (dirpath, dirnames, filenames) in chain.from_iterable(os.walk(path) for path in paths):
            for i in filenames:
                if any(i.endswith(ext) for ext in ['.ttf', '.otf', '.ttc', '.ttz', '.woff', '.woff2']):
                    fonts_path.append(dirpath.replace('\\\\', '\\') + '\\' + i)

        fonts = {ttLib.TTFont(p, fontNumber=1)['name'].getDebugName(4): p for p in fonts_path}

        fontfolderPath = Path(Utils.get_proj_path()) / "fonts"

        for obj in Utils.iterate_hierarchy(Utils.get_source_doc().GetFirstObject()):
            typename = obj.GetTypeName()
            if typename in ["Text Spline", "Text"]:
                nodeData = obj.GetData()
                fontData = nodeData[c4d.PRIM_TEXT_FONT]
                if fontData is None or len(fontData.GetFont()) < 1:
                    fontContainer = c4d.bitmaps.GeClipMap.GetDefaultFont(
                        c4d.GE_FONT_DEFAULT_SYSTEM)
                else:
                    fontContainer = fontData.GetFont()

                names_n = {500: fontContainer[500], 509: fontContainer[509]}

                for k, v in names_n.items():
                    if v in fonts:
                        # print(k, v, fonts[v])
                        if not Path.exists(fontfolderPath / Path(fonts[v]).name):
                            UaLog('font_used', dialog=self.dialog(), object=obj, name=v, filepath=fonts[v])
                            break

    def fix_save_font(self, path):
        proj_fontfolder = str(Path(Utils.get_proj_path()) / "fonts")
        if Utils.copyfile(path, proj_fontfolder):
            return True
        else:
            return False


class CheckAndFixPlugins(CheckAndFix):
    def GetThirdPartyPluginIds(self):
        pluginPaths = [str(url) for url in maxon.Application.GetModulePaths()]
        applicationPath = str(maxon.Application.GetUrl(maxon.APPLICATION_URLTYPE.STARTUP_DIR))
        pluginPaths = [path for path in pluginPaths if not path.startswith(applicationPath)]

        pluginPaths = [os.path.normpath(str(p).lower().replace("file:///", "", 1)) for p in pluginPaths]

        result = {}
        for plugin in c4d.plugins.FilterPluginList(type=c4d.PLUGINTYPE_ANY, sortbyname=False):
            fileName = os.path.normpath(plugin.GetFilename().lower())
            isExternal = any([fileName.startswith(path) for path in pluginPaths])
            if isExternal:
                result[plugin.GetID()] = f"{plugin.GetName()}, {fileName}"

        return result

    def check(self):
        thirdPartyPluginIds = self.GetThirdPartyPluginIds()
        for obj in Utils.iterate_hierarchy(Utils.get_source_doc().GetFirstObject()):
            if obj.GetType() in thirdPartyPluginIds.keys():
                UaLog('plugin_thirdparty', dialog=self.dialog(), object=obj)

            for tag in obj.GetTags():
                if tag.GetType() in thirdPartyPluginIds.keys():
                    UaLog('plugin_thirdparty', dialog=self.dialog(), object=tag)


class Worker():
    def __init__(self, dialog):
        # Handler.__init__(self)
        self.dialog = weakref.ref(dialog)
        self.useTakes = False
        self.mocache_paths = []

        self.ch_textures = CheckAndFixTextures(self)
        self.ch_render_settings = CheckAndFixRenderSettings(self)
        self.ch_assets = CheckAndFixAssets(self)
        self.ch_cache = CheckAndFixCache(self)
        self.ch_plugins = CheckAndFixPlugins(self)
        self.ch_fonts = CheckAndFixFonts(self)
        self.collect_scene = CollectScene()

    def collect_old(self):
        collected = self.collect_scene.is_collected()
        if collected:
            self.dialog().set_status("col_ok_already")
            return True
        else:
            saved = self.collect_scene._save_project_assets()
            if saved:
                loaded = self.collect_scene._load_doc()
                if loaded:
                    self.dialog().set_status("col_ok")
                    return True
                else:
                    self.dialog().set_status("col_err_open")
            else:
                self.dialog().set_status("col_err_save")

        return False

    def collect(self):
        self.dialog().set_status("col_ok")
        return True


    def checks(self):
        self.ch_textures.check()
        self.ch_render_settings.check()
        self.ch_assets.check()
        self.ch_cache.check()
        self.ch_plugins.check()
        self.ch_fonts.check()

        """for f in self.__all_checks:
            f()"""


class CustomLineText():
    def __init__(self, UA, pos_x):
        self.UA = weakref.ref(UA)
        self.pos_x = pos_x
        self.UA().DrawSetFont(c4d.FONT_DEFAULT)
        self.line_h = self.UA().DrawGetFontHeight()
        self.parse_text()

    def parse_text(self):
        text_list = re.split(r'({OBJ}|{NAME}|{LINK})', self.UA().text)
        self.text_for_line = []
        offset_x = 0

        for i, txt in enumerate(text_list):
            self.UA().DrawSetFont(c4d.FONT_DEFAULT)
            if txt == "{OBJ}":
                self.UA().DrawSetFont(c4d.FONT_BOLD)
                txt = self.UA().object.GetName()
                self.UA().buttons.append(LogButton(self.UA(), "object_link", text=txt, btn_x=self.pos_x + offset_x))
            elif txt == "{LINK}":
                txt = "our website"
                self.UA().buttons.append(LogButton(self.UA(), "web_link", text=txt, btn_x=self.pos_x + offset_x))
            elif txt == "{NAME}":
                txt = self.UA().name
                self.UA().buttons.append(LogButton(self.UA(), "name", text=txt, btn_x=self.pos_x + offset_x))
            else:
                if self.UA().log_type in ["tex_missing", "tex_char"]:
                    txt = self.UA().object["assetname"]

                self.text_for_line.append([txt, offset_x])
            offset_x += self.UA().DrawGetTextWidth(txt)

    def draw(self):
        self.UA().DrawSetFont(c4d.FONT_DEFAULT)
        btn_y1 = int(self.UA().h * 0.5 - self.line_h * 0.5)
        for txt, offset_x in self.text_for_line:
            self.UA().DrawSetTextCol(COLOR_TEXT, c4d.COLOR_TRANS)
            self.UA().DrawText(txt, offset_x + self.pos_x, btn_y1)


class UaBreadcrumb(c4d.gui.GeUserArea):

    def __init__(self, text='', dialog=None):
        self.dialog = weakref.ref(dialog)
        self.text = text
        self.w = self.GetWidth()
        self.h = self.GetHeight()

        self.err_cnt = 0

    def InitValues(self):
        return True

    def Sized(self, w, h):
        self.w, self.h = w, h

    def InputEvent(self, msg):

        return True

    def Message(self, msg, result):

        return super(UaBreadcrumb, self).Message(msg, result)

    def DrawMsg(self, x1, y1, x2, y2, msg):
        d = {"Collect": 0, "Check": 1, "Send": 2}
        circ_bmp = self.dialog().circ_ok

        if self.dialog().page >= d[self.text]:
            clr = COLOR_WHITE
            if self.err_cnt > 0 and d[self.text] == 1:
                circ_bmp = self.dialog().circ_warning
        else:
            clr = COLOR_GRAY
            circ_bmp = self.dialog().circ_gray

        self.OffScreenOn()
        self.SetClippingRegion(x1, y1, x2, y2)
        self.DrawSetPen(COLOR_BG)
        self.DrawRectangle(x1, y1, x2, y2)

        self.DrawSetFont(c4d.FONT_BOLD)
        text_h = self.DrawGetFontHeight()

        w = circ_bmp.GetBw()
        h = circ_bmp.GetBh()
        scale = 4
        x1_circ = x1
        y1_circ = self.h - int(text_h * 0.5 + h * 0.5 / scale) - 9

        text_offset = int(w / scale) + 10
        if d[self.text] == 1:
            if self.err_cnt > 0:
                self.DrawSetFont(c4d.FONT_DEFAULT)
                err_cnt_w = self.DrawGetTextWidth(str(self.err_cnt))
                err_cnt_h = self.DrawGetFontHeight()

                x1_err_cnt = x1_circ + int(w / scale) + 3
                y1_err_cnt = self.h - int(text_h * 0.5 + err_cnt_h * 0.5) - 9

                self.DrawSetTextCol(COLOR_GRAY, COLOR_TRANS)
                self.DrawText(str(self.err_cnt), x1_err_cnt, y1_err_cnt)

                text_offset = x1_err_cnt + err_cnt_w + 10

                self.DrawSetFont(c4d.FONT_BOLD)

        self.DrawBitmap(circ_bmp, x1_circ, y1_circ, int(w / scale), int(h / scale), 0, 0, w, h,
                        c4d.BMP_NORMALSCALED | c4d.BMP_ALLOWALPHA)

        self.DrawSetPen(clr)
        self.DrawRectangle(0, self.h - 1, self.w, self.h)

        self.DrawSetTextCol(clr, COLOR_BG)
        self.DrawText(self.text, text_offset, self.h - text_h - 9)


class UaTitle(c4d.gui.GeUserArea):
    def __init__(self, dialog):
        self.dialog = weakref.ref(dialog)
        self.bmp_1 = self.DrawTextBmp("Collect Project")
        self.bmp_2 = self.DrawTextBmp("Check Project")
        self.bmp_3 = self.DrawTextBmp("Send Project")
        self.w_1 = self.bmp_1.GetBw()
        self.h_1 = self.bmp_1.GetBh()
        self.w_2 = self.bmp_2.GetBw()
        self.h_2 = self.bmp_2.GetBh()
        self.w_3 = self.bmp_3.GetBw()
        self.h_3 = self.bmp_3.GetBh()

        self.w = self.GetWidth()
        self.h = self.GetHeight()

    def Sized(self, w, h):
        self.w = w
        self.h = h

    def DrawTextBmp(self, txt):
        myGeClipMap = c4d.bitmaps.GeClipMap()
        if myGeClipMap is None:
            raise RuntimeError("Failed to create a GeClipMap")

        if not myGeClipMap.Init(1, 1):
            raise RuntimeError("Failed to initialize GeClipMap")

        myGeClipMap.BeginDraw()
        bc = c4d.bitmaps.GeClipMap.GetFontDescription("SegoeUI-Semilight", c4d.GE_FONT_NAME_POSTSCRIPT)
        c4d.bitmaps.GeClipMap.SetFontSize(bc, c4d.GE_FONT_SIZE_INTERNAL, 50)
        myGeClipMap.SetFont(bc, 0.0)

        w = myGeClipMap.TextWidth(txt)
        h = myGeClipMap.TextHeight()

        myGeClipMap.EndDraw()
        myGeClipMap.Destroy()

        if not myGeClipMap.Init(w, h):
            raise RuntimeError("Failed to initialize GeClipMap")

        myGeClipMap.BeginDraw()
        myGeClipMap.SetFont(bc, 0.0)
        myGeClipMap.SetColor(255, 255, 255, 255)
        myGeClipMap.TextAt(0, 0, txt)
        myGeClipMap.EndDraw()

        bitmap = myGeClipMap.GetBitmap().GetClone()
        alphaChannel = bitmap.AddChannel(True, False)
        myGeClipMap.BeginDraw()
        for x in range(w):
            for y in range(h):
                r, g, b, a = myGeClipMap.GetPixelRGBA(x, y)
                bitmap.SetPixel(x, y, 255, 255, 255)
                bitmap.SetAlphaPixel(alphaChannel, x, y, r)
        myGeClipMap.EndDraw()

        return bitmap

    def DrawMsg(self, x1, y1, x2, y2, msg):
        self.OffScreenOn()
        self.SetClippingRegion(x1, y1, x2, y2)
        self.DrawSetPen(COLOR_BG)
        self.DrawRectangle(x1, y1, x2, y2)

        page = self.dialog().page
        if page == 0:
            w = self.w_1
            h = self.h_1
            bmp = self.bmp_1
        elif page == 1:
            w = self.w_2
            h = self.h_2
            bmp = self.bmp_2
        elif page == 2:
            w = self.w_3
            h = self.h_3
            bmp = self.bmp_3

        scalefactor = 0.9
        x = int(70)
        y = int(self.h * 0.5 - h * scalefactor * 0.5)

        self.DrawBitmap(bmp, x, y, int(w * scalefactor), int(h * scalefactor), 0, 0, w, h,
                        c4d.BMP_NORMALSCALED | c4d.BMP_ALLOWALPHA)


class DrawElements():
    def __init__(self):
        pass

    @staticmethod
    def draw_outline(UA, x1, y1, x2, y2, color):
        x2 -= 1
        y2 -= 1
        UA().DrawSetPen(color)
        # arc0
        points = array.array('f', range(6))
        points[0] = x1
        points[1] = 5.85 + y1
        points[2] = 5.85 + x1
        points[3] = y1
        points[4] = 10.0 + x1
        points[5] = y1
        UA().DrawBezier(x1, 10.0 + y1, points, False, False)
        # line0
        points[0] = 10.0 + x1
        points[1] = y1
        points[2] = x2 - 10.0
        points[3] = y1
        points[4] = x2 - 10.0
        points[5] = y1
        UA().DrawBezier(10.0 + x1, y1, points, False, False)
        # arc1
        points[0] = x2 - 10.0 + 5.85
        points[1] = y1
        points[2] = x2
        points[3] = y1 + 10 - 5.85
        points[4] = x2
        points[5] = y1 + 10
        UA().DrawBezier(x2 - 10.0, y1, points, False, False)
        # line1
        points[0] = x2
        points[1] = y1 + 10
        points[2] = x2
        points[3] = y2 - 10.0
        points[4] = x2
        points[5] = y2 - 10.0
        UA().DrawBezier(x2, y1 + 10, points, False, False)
        # arc2
        points[0] = x2
        points[1] = y2 - 10.0 + 5.85
        points[2] = x2 - 10.0 + 5.85
        points[3] = y2
        points[4] = x2 - 10.0
        points[5] = y2
        UA().DrawBezier(x2, y2 - 10.0, points, False, False)
        # line2
        points[0] = x2 - 10.0
        points[1] = y2
        points[2] = x1 + 10.0
        points[3] = y2
        points[4] = x1 + 10.0
        points[5] = y2
        UA().DrawBezier(x2 - 10.0, y2, points, False, False)
        # arc3
        points[0] = x1 + 10 - 5.85
        points[1] = y2
        points[2] = x1
        points[3] = y2 - 10.0 + 5.85
        points[4] = x1
        points[5] = y2 - 10.0
        UA().DrawBezier(x1 + 10.0, y2, points, False, False)
        # line3
        points[0] = x1
        points[1] = y2 - 10.0
        points[2] = x1
        points[3] = 10.0 + y1
        points[4] = x1
        points[5] = 10.0 + y1
        UA().DrawBezier(x1, y2 - 10.0, points, False, False)

    @staticmethod
    def draw_bmp(UA, bmp, x, y, scale, color_bg):
        w = bmp.GetBw()
        h = bmp.GetBh()
        UA().DrawSetPen(color_bg)
        UA().DrawBitmap(bmp, x, y, int(w / scale), int(h / scale), 0, 0, w, h,
                        c4d.BMP_NORMALSCALED | c4d.BMP_ALLOWALPHA)

    @staticmethod
    def get_text_h(UA, type=0):
        DrawElements.set_font(UA, type=type)
        text_h = UA().DrawGetFontHeight()
        return text_h

    @staticmethod
    def get_text_w(UA, text, type=0):
        DrawElements.set_font(UA, type=type)
        text_w = UA().DrawGetTextWidth(text)
        return text_w

    @staticmethod
    def set_font(UA, type=0):
        if type == 0:
            font_type = c4d.FONT_DEFAULT
        elif type == 1:
            font_type = c4d.FONT_BOLD
        UA().DrawSetFont(font_type)

    @staticmethod
    def draw_text_v(UA, txt, x, y1, y2, type=0, color=COLOR_WHITE):
        DrawElements.set_font(UA, type=type)
        UA().DrawSetTextCol(color, COLOR_TRANS)
        text_h = DrawElements.get_text_h(UA, type=type)
        txt_y = int((y1 + y2 - text_h) * 0.5)
        UA().DrawText(txt, x, txt_y)

    @staticmethod
    def draw_text_bl(UA, txt, x1, x2, y1, y2, type=1, color=COLOR_WHITE):
        DrawElements.draw_text_v(UA, txt, x1, y1, y2, type=type, color=color)
        bl = UA().DrawGetFontBaseLine() + 1
        UA().DrawSetPen(color)
        UA().DrawLine(x1, y1 + bl, x2, y1 + bl)

    @staticmethod
    def draw_circ_digits(UA, bmp, digits, x1, y1, x2, y2, scale=3, offset=0, gap=3, type=0, color=COLOR_GRAY):
        DrawElements.set_font(UA, type=type)

        bmp_h = bmp.GetBh()
        bmp_w = bmp.GetBw()

        bmp_x = x1 + offset
        bmp_y = int((y1 + y2 - bmp_h / scale) * 0.5)
        DrawElements.draw_bmp(UA, bmp, bmp_x, bmp_y, scale, COLOR_BG)

        txt_x = int(bmp_x + bmp_w / scale + gap)
        DrawElements.draw_text_v(UA, digits, txt_x, y1, y2, color=color)


class LacButton():
    def __init__(self, constr_h=False, constr_v=False, constr_l=True, constr_t=True,
                 btn_x=0, btn_y=0, btn_w=0, btn_h=0,
                 offset_l=0, offset_r=0, offset_t=0, offset_b=0):
        self.constr_h = constr_h
        self.constr_v = constr_v
        self.constr_l = constr_l
        self.constr_t = constr_t
        self.offset_l = offset_l
        self.offset_r = offset_r
        self.offset_t = offset_t
        self.offset_b = offset_b
        self.btn_x = btn_x
        self.btn_y = btn_y
        self.btn_w = btn_w
        self.btn_h = btn_h

        self.over_btn = False
        self.pressed = False
        pass

    def is_over_button(self, x, y):
        x1, y1, x2, y2 = self.get_coord()
        is_over = x1 < x < x2 and y1 < y < y2
        if is_over:
            return True
        else:
            return False

    def get_coord(self):
        w = self.UA().w
        h = self.UA().h
        if self.constr_h:
            x1 = int(w * self.btn_x + self.offset_l)
            x2 = int(w * self.btn_x + w * self.btn_w + self.offset_r)
        else:
            if self.constr_l:
                x1 = self.btn_x
                x2 = self.btn_x + self.btn_w
            else:
                x1 = w - self.btn_x
                x2 = w - self.btn_x + self.btn_w

        if self.constr_v:
            y1 = int(h * self.btn_y + self.offset_t)
            y2 = int(h * self.btn_y + h * self.btn_h + self.offset_b)
        else:
            if self.constr_t:
                y1 = self.btn_y
                y2 = self.btn_y + self.btn_h
            else:
                y1 = h - self.btn_y
                y2 = h - self.btn_y + self.btn_h
        return x1, y1, x2, y2


class LacButtonsUA(c4d.gui.GeUserArea):
    def __init__(self):
        pass

    def InitValues(self):
        self.buttons = []
        self.w = self.GetWidth()
        self.h = self.GetHeight()

        self.add_buttons()
        return True

    def InputEvent(self, msg):
        # Do nothing if its not a left mouse click event
        if msg[c4d.BFM_INPUT_DEVICE] != c4d.BFM_INPUT_MOUSE or msg[c4d.BFM_INPUT_CHANNEL] != c4d.BFM_INPUT_MOUSELEFT:
            return True

        base = self.Local2Global()
        mousex = msg[c4d.BFM_INPUT_X] - base['x']
        mousey = msg[c4d.BFM_INPUT_Y] - base['y']
        for btn in self.buttons:
            if btn.is_over_button(mousex, mousey):
                self.MouseDragStart(c4d.KEY_MLEFT, mousex, mousey,
                                    c4d.MOUSEDRAGFLAGS_DONTHIDEMOUSE | c4d.MOUSEDRAGFLAGS_NOMOVE)
                initial_state = btn.pressed
                btn.pressed = True
                self.Redraw()  # Redraw after press button

                mx = mousex
                my = mousey
                isFirstTick = True
                while True:
                    if msg[c4d.BFM_INPUT_VALUE] == 0:
                        break
                    result, dx, dy, channels = self.MouseDrag()
                    if result != c4d.MOUSEDRAGRESULT_CONTINUE:
                        break
                    if isFirstTick:
                        isFirstTick = False
                        continue
                    if dx == 0.0 and dy == 0.0:
                        continue
                    mx -= dx
                    my -= dy

                end_state = self.MouseDragEnd()

                if end_state == c4d.MOUSEDRAGRESULT_ESCAPE:
                    pass
                elif end_state == c4d.MOUSEDRAGRESULT_FINISHED:
                    if btn.is_over_button(mx, my):
                        self.button_action(btn)
                    else:
                        btn.pressed = initial_state

                    self.Redraw()  # Redraw after release button

                return True

        return True

    def Sized(self, w, h):
        self.w = w
        self.h = h

    def draw_buttons(self):
        for btn in self.buttons:
            btn.draw()

    def DrawMsg(self, x1, y1, x2, y2, msg):
        self.OffScreenOn()
        self.DrawSetPen(COLOR_BG)
        self.DrawRectangle(x1, y1, x2, y2)
        self.draw()

    def Message(self, msg, result):
        if msg.GetId() == c4d.BFM_TIMER_MESSAGE:
            for btn in self.buttons:
                btn.over_btn = False
            self.Redraw()  # Redraw after moved out user area
            return True

        if msg.GetId() == c4d.BFM_GETCURSORINFO:
            base = self.Local2Global()
            bc = c4d.BaseContainer()
            res = self.GetInputState(c4d.BFM_INPUT_MOUSE,
                                     c4d.BFM_INPUT_MOUSELEFT, bc)
            mx = bc.GetLong(c4d.BFM_INPUT_X) - base['x']
            my = bc.GetLong(c4d.BFM_INPUT_Y) - base['y']
            for btn in self.buttons:
                if btn.is_over_button(mx, my):
                    btn.cursor(result)
                    self.ActivateFading(1)
                    if not btn.over_btn:
                        btn.over_btn = True
                        self.Redraw()
                else:
                    if btn.over_btn:
                        btn.over_btn = False
                        self.Redraw()

            return True

        return super(LacButtonsUA, self).Message(msg, result)


class LogButton(LacButton):
    def __init__(self, UA, btn_type="", text="", weblink="", btn_x=0, constr_l=True):
        super(LogButton, self).__init__(constr_l=constr_l, btn_x=btn_x)
        self.UA = weakref.ref(UA)
        self.text = text
        self.btn_type = btn_type
        self.btn_w = DrawElements.get_text_w(self.UA, self.text, type=1)
        self.btn_h = DrawElements.get_text_h(self.UA, type=1)
        self.btn_x = btn_x
        if not constr_l:
            if self.btn_type == "tex_relink":
                self.btn_x = 155
            else:
                self.btn_x = 84
        self.btn_y = int((self.UA().h - self.btn_h) * 0.5)

        self.weblink = weblink
        self.fixed = False

    def draw(self):
        if self.over_btn:
            btn_color = c4d.COLOR_TEXT_HIGHLIGHT_1_UNUSED
        else:
            btn_color = COLOR_TEXT
        if self.pressed:
            btn_color = c4d.COLOR_SB_TEXT_ACTIVE2

        if self.btn_type == "name":
            btn_color = COLOR_TEXT

        x1, y1, x2, y2 = self.get_coord()

        if self.btn_type in ["object_link", "name"]:
            DrawElements.draw_text_v(self.UA, self.text, x1, y1, y2, type=1, color=btn_color)
        else:
            DrawElements.draw_text_bl(self.UA, self.text, x1, x2, y1, y2)

    def cursor(self, result):
        if not self.btn_type == "name":
            result.SetId(c4d.BFM_GETCURSORINFO)
            result.SetInt32(c4d.RESULT_CURSOR, c4d.MOUSE_POINT_HAND)
            result.SetString(c4d.RESULT_BUBBLEHELP, "Read the manual\nfor further explanation")


class UaLog(LacButtonsUA):
    def __init__(self, log_type, dialog=None, object=None, name="", filepath=""):
        self.UA = weakref.ref(self)
        self.log_type = log_type
        self.dialog = dialog
        self.object = object
        self.name = name
        self.filepath = filepath
        self.row_status = ROW_TXT[log_type]["type"]

        self.circ_bmp = self.dialog.circ_ok
        if self.row_status == "warning":
            self.circ_bmp = self.dialog.circ_warning
        elif self.row_status == "error":
            self.circ_bmp = self.dialog.circ_error

        self.circ_w = self.circ_bmp.GetBw()
        self.circ_h = self.circ_bmp.GetBh()
        self.circ_scale = 3

        category = log_type.split("_")[0]

        row_colors = [COLOR_LINE0, COLOR_LINE1]
        self.bg_color = row_colors[0]
        parent_list = []
        if category == "tex":
            parent_list = self.dialog.list_textures
        elif category == "ren":
            parent_list = self.dialog.list_render
        elif category == "asset":
            parent_list = self.dialog.list_assets
        elif category == "cache":
            parent_list = self.dialog.list_cache
        elif category == "plugin":
            parent_list = self.dialog.list_plugins
        elif category == "font":
            parent_list = self.dialog.list_fonts

        self.bg_color = row_colors[len(parent_list) % 2]
        parent_list.append(self)

        self.text = ""

        if log_type in ROW_TXT:
            self.text = ROW_TXT[log_type]["text"]

        self.bc = c4d.BaseContainer()
        self.w = self.GetWidth()
        self.h = self.GetHeight()
        self.fixed = False

    def draw(self):
        self.OffScreenOn()
        self.SetClippingRegion(0, 0, self.w, self.h)
        self.DrawSetPen(self.bg_color)
        self.DrawRectangle(0, 0, self.w, self.h)

        bmp_h = self.circ_bmp.GetBh()
        bmp_w = self.circ_bmp.GetBw()
        bmp_scale = 3
        bmp_x = self.w - int(bmp_w / bmp_scale)
        bmp_y = int((0 + self.h - bmp_h / bmp_scale) * 0.5)

        DrawElements.draw_bmp(self.UA, self.circ_bmp, bmp_x, bmp_y, bmp_scale, self.bg_color)

        self.line_text.draw()
        self.draw_buttons()

    def add_buttons(self):
        if self.fixed and "btn_fixed" in ROW_TXT[self.log_type]:
            for b in ROW_TXT[self.log_type]["btn_fixed"]:
                self.buttons.append(LogButton(self, constr_l=False, **b))
        else:
            for b in ROW_TXT[self.log_type]["btn"]:
                self.buttons.append(LogButton(self, constr_l=False, **b))

        self.line_text = CustomLineText(self, 10)

    def set_fixed(self):
        self.fixed = True
        self.circ_bmp = self.dialog.circ_ok
        self.buttons = []
        self.text = ROW_TXT[self.log_type]["text_fixed"]
        self.line_text.parse_text()

        if "btn_fixed" in ROW_TXT[self.log_type]:
            for b in ROW_TXT[self.log_type]["btn_fixed"]:
                self.buttons.append(LogButton(self, **b))

        self.Redraw()

    def button_action(self, btn):
        if btn.btn_type == 'tex_relink':
            fixed = Utils.relink_asset(self.object)
            if fixed:
                btn.fixed = True
                self.set_fixed()

        elif btn.btn_type == 'tex_clear':
            self.dialog.worker.ch_textures.fix_clear_texture(self.object)
            self.dialog.list_textures.remove(self)
            self.dialog.add_rows()

        elif btn.btn_type == 'fix_ren_paths':
            self.dialog.worker.ch_render_settings.fix_output_name()
            btn.fixed = True
            self.set_fixed()

        elif btn.btn_type == 'scroll_to':
            Utils.scroll_to(self.object)

        elif btn.btn_type == 'bake':
            fixed = self.dialog.worker.ch_cache.fix_bake(self.object)
            if fixed:
                btn.fixed = True
                self.set_fixed()
        elif btn.btn_type == 'web':
            webbrowser.open(btn.weblink, new=2)

        elif btn.btn_type == 'object_link':
            Utils.scroll_to(self.object)

        elif btn.btn_type == 'save':
            fixed = self.dialog.worker.ch_fonts.fix_save_font(btn.UA().filepath)
            if fixed:
                btn.fixed = True
                self.set_fixed()

        btn.pressed = False


class TabButton(LacButton):
    def __init__(self, UA, log_type, btn_x, btn_y, offset_l, offset_r, offset_t, offset_b):
        super(TabButton, self).__init__(constr_h=True, constr_v=True, btn_x=btn_x, btn_y=btn_y,
                                        btn_w=0.333, btn_h=0.5,
                                        offset_l=offset_l, offset_r=offset_r, offset_t=offset_t, offset_b=offset_b)
        self.UA = weakref.ref(UA)
        self.err_cnt = 0
        self.text = ""
        self.log_type = log_type
        if self.log_type == "textures":
            self.text = "Textures"
            self.err_cnt = len(self.UA().dialog().list_textures)
        elif self.log_type == "render":
            self.text = "Render Settings"
            self.err_cnt = len(self.UA().dialog().list_render)
        elif self.log_type == "assets":
            self.text = "Assets"
            self.err_cnt = len(self.UA().dialog().list_assets)
        elif self.log_type == "cache":
            self.text = "Cache"
            self.err_cnt = len(self.UA().dialog().list_cache)
        elif self.log_type == "plugins":
            self.text = "Plugins"
            self.err_cnt = len(self.UA().dialog().list_plugins)
        elif self.log_type == "fonts":
            self.text = "Fonts"
            self.err_cnt = len(self.UA().dialog().list_fonts)

    def draw(self):
        if self.over_btn:
            btn_color = COLOR_TEXT
        else:
            btn_color = COLOR_GRAY
        if self.pressed:
            btn_color = COLOR_WHITE

        x1, y1, x2, y2 = self.get_coord()

        if self.err_cnt == 0:
            circ_bmp = self.UA().dialog().circ_ok
        else:
            circ_bmp = self.UA().dialog().circ_warning

        DrawElements.draw_circ_digits(self.UA, circ_bmp, self.err_cnt, x1, y1, x2, y2, offset=19)
        DrawElements.draw_text_v(self.UA, self.text, x1 + 61, y1, y2, color=btn_color)
        DrawElements.draw_outline(self.UA, x1, y1, x2, y2, btn_color)

    def cursor(self, result):
        pass


class UaTabs(LacButtonsUA):

    def __init__(self, dialog):
        self.dialog = weakref.ref(dialog)

    def draw(self):
        self.draw_buttons()

    def add_buttons(self):
        self.buttons.append(TabButton(self, "textures", 0, 0, 0, -7, 0, -7))
        self.buttons.append(TabButton(self, "render", 0.333, 0, 7, -7, 0, -7))
        self.buttons.append(TabButton(self, "assets", 0.666, 0, 7, 0, 0, -7))
        self.buttons.append(TabButton(self, "cache", 0, 0.5, 0, -7, 7, 0))
        self.buttons.append(TabButton(self, "plugins", 0.333, 0.5, 7, -7, 7, 0))
        self.buttons.append(TabButton(self, "fonts", 0.666, 0.5, 7, 0, 7, 0))
        i = ["textures", "render", "assets", "cache", "plugins", "fonts"].index(self.dialog().active_category)
        self.buttons[i].pressed = True

    def button_action(self, btn):
        for b in self.buttons:
            if b != btn:
                b.pressed = False
        self.dialog().active_category = btn.log_type
        self.dialog().add_rows()

    def GetMinSize(self):
        return 100, 100


class LACRIMASDialog(gui.GeDialog):
    def __init__(self):
        # self.worker = None
        self.worker = Worker(self)
        self.page = 0
        self.active_category = "textures"
        self.ua_brcr_collect = UaBreadcrumb("Collect", self)
        self.ua_brcr_check = UaBreadcrumb("Check", self)
        self.ua_brcr_send = UaBreadcrumb("Send", self)
        self.ua_title = UaTitle(self)
        self.circ_ok = self.draw_circ_bmp("ok")
        self.circ_warning = self.draw_circ_bmp("warning")
        self.circ_error = self.draw_circ_bmp("error")
        self.circ_gray = self.draw_circ_bmp("gray")

    def InitValues(self):
        self.list_textures = []
        self.list_render = []
        self.list_assets = []
        self.list_cache = []
        self.list_plugins = []
        self.list_fonts = []

        return True

    def draw_circ_bmp(self, circ_type):
        scale = 3
        w = 16 * scale
        h = 16 * scale
        myGeClipMap = c4d.bitmaps.GeClipMap()
        if myGeClipMap is None:
            raise RuntimeError("Failed to create a GeClipMap")

        if not myGeClipMap.Init(w, h):
            raise RuntimeError("Failed to initialize GeClipMap")

        myGeClipMap.BeginDraw()
        if circ_type == "ok":
            clr = self.GetColorRGB(COLOR_GREEN)
        elif circ_type == "warning":
            clr = self.GetColorRGB(COLOR_ORANGE)
        elif circ_type == "error":
            clr = self.GetColorRGB(COLOR_RED)
        elif circ_type == "gray":
            clr = self.GetColorRGB(COLOR_GRAY)

        myGeClipMap.SetColor(clr["r"], clr["g"], clr["b"], 0)

        myGeClipMap.FillEllipse(scale, scale, w - scale, h - scale)
        myGeClipMap.EndDraw()

        bitmap = myGeClipMap.GetBitmap().GetClone()

        alphaChannel = bitmap.AddChannel(True, False)
        myGeClipMap.BeginDraw()
        for x in range(w):
            for y in range(h):
                r, g, b, a = myGeClipMap.GetPixelRGBA(x, y)
                bitmap.SetPixel(x, y, clr["r"], clr["g"], clr["b"])
                bitmap.SetAlphaPixel(alphaChannel, x, y, 255 - a)
        myGeClipMap.EndDraw()

        return bitmap

    def set_page(self):
        if self.page == 0:
            self.page_collect()
        elif self.page == 1:
            self.page_check()
        elif self.page == 2:
            self.page_send()
        self.element_hide()

    def check_project(self):
        self.worker.checks()
        self.add_rows()

    def add_rows(self):
        rows = []
        category = self.active_category
        if category == "textures":
            rows = self.list_textures
        elif category == "render":
            rows = self.list_render
        elif category == "assets":
            rows = self.list_assets
        elif category == "cache":
            rows = self.list_cache
        elif category == "plugins":
            rows = self.list_plugins
        elif category == "fonts":
            rows = self.list_fonts
        self.space_group(rows)
        self.LayoutChanged(res.GRP_VIEWS)

    def space_group(self, len_area):  # BUG UI
        self.LayoutFlushGroup(res.GRP_VIEWS)
        self.ScrollGroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, c4d.SCROLLGROUP_VERT,
                              0, 0)
        self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, 0, len(len_area), "")

        self.GroupSpace(0, 0)

        for index, area in enumerate(len_area):
            self.GroupBegin(index, c4d.BFH_SCALEFIT, 0, 0, "", 0, c4d.gui.SizePix(660), c4d.gui.SizePix(40))
            area = self.AddUserArea((index + 1) * 100, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT)
            self.AttachUserArea(len_area[index], area)
            self.GroupEnd()
        self.GroupEnd()
        self.GroupEnd()

    def element_hide(self):
        if self.page == 0:
            self.HideElement(res.BTN_REFRESH, True)
            self.HideElement(res.BTN_PREV, True)
        elif self.page == 1:
            self.HideElement(res.BTN_REFRESH, False)
            self.HideElement(res.BTN_PREV, False)
        elif self.page == 2:
            self.HideElement(res.BTN_REFRESH, False)
            self.HideElement(res.BTN_PREV, False)

        self.LayoutChanged(res.GRP_BACK_FOV)

    def page_collect(self):  # BUG UI

        self.LayoutFlushGroup(res.GRP_DYNPAGE)
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=1, rows=0)
        self.AddStaticText(res.IDS_PROJNAME, flags=c4d.BFH_SCALEFIT | c4d.BFH_RIGHT, name='Project name')  # dummy line
        self.GroupBorderSpace(70, 0, 70, 0)

        settings = c4d.BaseContainer()
        settings.SetBool(c4d.FILENAME_SAVE, True)

        self.AddCustomGui(res.EDS_PROJNAME, c4d.CUSTOMGUI_FILENAME, "", c4d.BFH_SCALEFIT, 50, 10, settings)

        self.SetString(res.EDS_PROJNAME, Utils.get_proj_path())

        self.GroupEnd()

        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2, rows=0)
        self.GroupBorderSpace(70, 70, 70, 0)

        """Creates the layout for the dialog.
        """
        bc = c4d.BaseContainer()
        bc[c4d.BITMAPBUTTON_BUTTON] = True
        # bc[c4d.BITMAPBUTTON_ICONID1] = c4d.OBJECT_FIGURE
        bc[c4d.BITMAPBUTTON_BACKCOLOR] = COLOR_BG
        bc[c4d.BITMAPBUTTON_DISABLE_FADING] = False
        bc[c4d.BITMAPBUTTON_FORCE_SIZE] = 24

        self.GroupBegin(res.GRP_CALC, c4d.BFH_LEFT, cols=2, rows=0)
        bmp_calc = load_bitmap('res/calculator.png')
        bmp_calc_w = c4d.gui.SizePix(24)
        bmp_calc_h = c4d.gui.SizePix(24)
        self.bitmapButton = self.AddCustomGui(res.BTN_CALC,
                                              c4d.CUSTOMGUI_BITMAPBUTTON, "",
                                              c4d.BFH_LEFT,
                                              bmp_calc_w, bmp_calc_h, bc)
        self.bitmapButton.SetImage(bmp_calc, True)

        self.AddStaticText(res.IDS_CALC, flags=c4d.BFH_LEFT, name='Calculator')
        self.GroupEnd()

        self.GroupBegin(res.GRP_INSTRUCT, c4d.BFH_LEFT, cols=2, rows=0)
        self.GroupBorderSpace(45, 0, 0, 0)
        bmp_instruct = load_bitmap('res/instruct.png')
        bmp_instruct_w = c4d.gui.SizePix(24)
        bmp_instruct_h = c4d.gui.SizePix(24)
        self.bitmapButton_2 = self.AddCustomGui(res.BTN_INSTRUCT,
                                                c4d.CUSTOMGUI_BITMAPBUTTON, "",
                                                c4d.BFH_LEFT,
                                                bmp_instruct_w, bmp_instruct_h, bc)
        self.bitmapButton_2.SetImage(bmp_instruct, True)
        self.AddStaticText(res.IDS_INSTRUCT, flags=c4d.BFH_LEFT, name='Instruction')
        self.GroupEnd()

        self.GroupEnd()
        self.LayoutChanged(res.GRP_DYNPAGE)

    def page_check(self):  # BUG UI

        self.LayoutFlushGroup(res.GRP_DYNPAGE)

        self.GroupBegin(id=res.GRP_TABS, flags=c4d.BFH_SCALEFIT, cols=1, rows=0, inith=c4d.gui.SizePix(116))
        self.GroupBorderSpace(70, 0, 70, 0)
        self.GroupBorderNoTitle(borderstyle=c4d.BORDER_NONE)

        area = self.AddUserArea(res.UA_TABS, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT)
        self.tabs = UaTabs(self)
        self.AttachUserArea(self.tabs, area)
        self.GroupEnd()

        self.GroupBegin(id=res.GRP_VIEWS, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1, rows=0, initw=0, inith=200)
        self.GroupBorderSpace(70, 0, 70, 0)
        self.GroupBorderNoTitle(borderstyle=c4d.BORDER_NONE)

        self.list_textures = []
        self.list_render = []
        self.list_assets = []
        self.list_cache = []
        self.list_plugins = []
        self.list_fonts = []

        collected = self.worker.collect_scene.is_collected()
        if collected:
            self.check_project()
        else:
            self.set_status("not_collected")

        self.GroupEnd()
        self.LayoutChanged(res.GRP_DYNPAGE)

        self.ua_brcr_check.err_cnt = sum(x.err_cnt for x in self.tabs.buttons)

    def page_send(self):

        self.LayoutFlushGroup(res.GRP_DYNPAGE)
        fl = c4d.BFH_SCALE | c4d.BFV_SCALE | c4d.BFV_CENTER
        fl_l = c4d.BFH_LEFT | fl
        fl_r = c4d.BFH_RIGHT | fl

        self.GroupBegin(res.GRP_SEND, flags=c4d.BFV_FIT | c4d.BFH_SCALEFIT, inith=c4d.gui.SizePix(0), cols=1)  # 1_begin
        self.GroupBorderSpace(70, 0, 70, 0)

        self.GroupBegin(res.GRP_SEND_BL_1, flags=c4d.BFV_FIT | c4d.BFV_TOP | c4d.BFH_SCALEFIT, inith=c4d.gui.SizePix(90),
                        rows=3,
                        cols=2)  # 2_begin

        self.AddStaticText(res.IDS_RENDER_ENGINE, flags=fl_l, name='Render Engine')
        engine_name = Utils.get_render_engine_name()
        self.AddStaticText(res.IDS_RENDER_ENGINE_VAL, flags=fl_r, name=engine_name)

        self.AddStaticText(res.IDS_RENDER_RES, flags=fl_l, name='Render Resolution')
        self.AddStaticText(res.IDS_RENDER_RES_VAL, flags=fl_r, name=Utils.get_render_res())

        self.AddStaticText(res.IDS_DUMMY, flags=fl_l, name='')  # dummy line

        self.GroupEnd()  # 2_end

        self.GroupBegin(res.GRP_SEND_BL_2, flags=c4d.BFV_FIT | c4d.BFV_TOP | c4d.BFH_SCALEFIT, inith=c4d.gui.SizePix(120),
                        cols=2)  # 3_begin

        self.AddStaticText(res.IDS_RATE, flags=fl_l, name='Rate')

        self.AddRadioGroup(res.RBGR_RATE, flags=fl_r, columns=2, rows=0)
        self.AddChild(res.RBGR_RATE, 0, 'Standart')
        self.AddChild(res.RBGR_RATE, 1, 'Rocket')
        self.SetInt32(res.RBGR_RATE, 0)

        self.AddStaticText(res.IDS_FRAMERANGE, flags=fl_l, name='Frame Range')

        self.GroupBegin(res.GRP_FRAMERANGE, flags=fl_r, cols=4)  # 4_begin
        start, end = Utils.get_frame_range()
        self.AddStaticText(res.IDS_FRAMERANGE_FROM, flags=fl_r, name='From')
        self.AddEditNumberArrows(res.NUM_FRAMERANGE_FROM, fl_r)
        self.SetInt32(res.NUM_FRAMERANGE_FROM, start)

        self.AddStaticText(res.IDS_FRAMERANGE_TO, flags=fl_r, name='To')
        self.AddEditNumberArrows(res.NUM_FRAMERANGE_TO, fl_r)
        self.SetInt32(res.NUM_FRAMERANGE_TO, end)

        self.GroupEnd()  # 4_end

        self.AddStaticText(res.IDS_FPT, flags=fl_l, name='Frame per task')
        self.AddRadioGroup(res.RBGR_FPT, flags=fl_r, columns=4, rows=0)
        self.AddChild(res.RBGR_FPT, 1, '1')
        self.AddChild(res.RBGR_FPT, 2, '5')
        self.AddChild(res.RBGR_FPT, 3, '10')
        self.AddChild(res.RBGR_FPT, 4, '25')
        self.SetInt32(res.RBGR_FPT, 1)
        self.AddStaticText(res.IDS_NOTIFY, flags=fl_l, name='Telegram Notification')
        self.AddEditText(res.EDS_NOTIFY, flags=fl_r, initw=c4d.gui.SizePix(195), editflags=c4d.EDITTEXT_HELPTEXT)
        self.SetString(res.EDS_NOTIFY, value="Your Telegram id", flags=c4d.EDITTEXT_HELPTEXT)

        self.GroupEnd()  # 3_end
        self.GroupEnd()  # 1_end

        self.LayoutChanged(res.GRP_DYNPAGE)

    def set_status(self, msg):
        txt = {"default":            'Input project name, and press "Next" button to collect scene',
               "col_ok_already":     "Project collected already",
               "col_ok":             "Project collected. We can start checking and resolving of errors",
               "col_err_open":       "At scene opening error was occurred.",
               "col_err_save":       "At scene collecting error was occured.",
               "not_collected":      "You need to collect scene at first. Return to 'Collect' page",
               "proj_name":          'Please, enter the project name',
               "proj_name_translit": 'Please, check the project name. Latin characters and digits allowed only. Spaces must be replaced by "_"'
               }
        self.SetString(res.IDS_STATUS_BAR, txt[msg])
        attention_status = ["col_err_save", "col_err_open"]
        if msg in attention_status:
            c4d.gui.MessageDialog(txt[msg])

    def CreateLayout(self):
        self.SetTitle("Lacrimas Renderfam Uploader")
        """data = c4d.BaseContainer()
        path  = self.GetFilename(FILENAME)
        data.SetString(1009,path)
        c4d.plugins.SetWorldPluginData(PLUGIN_ID,data) """

        breadcrumb_indent = 33
        breadcrumb_h = 26
        title_area_h = 130
        padding_bottom = 135

        self.GroupBegin(id=9999, flags=c4d.BFV_SCALEFIT | c4d.BFH_SCALEFIT, cols=1, initw=c4d.gui.SizePix(800))
        # self.GroupBorderNoTitle(c4d.BORDER_SCHEME_EDIT)
        # self.GroupBorderSpace(10, 10, 10, 10)

        self.GroupBegin(id=res.GRP_BRCR, flags=c4d.BFH_SCALEFIT, cols=3, rows=1)
        self.GroupBorderSpace(70, 0, 70, 0)
        self.GroupSpace(14, 0)

        self.AddUserArea(res.BRCR_COLLECT_AREA, c4d.BFH_SCALEFIT, inith=c4d.gui.SizePix(breadcrumb_indent + breadcrumb_h))
        self.AttachUserArea(self.ua_brcr_collect, res.BRCR_COLLECT_AREA)

        self.AddUserArea(res.BRCR_CHECK_AREA, c4d.BFH_SCALEFIT, inith=c4d.gui.SizePix(breadcrumb_indent + breadcrumb_h))
        self.AttachUserArea(self.ua_brcr_check, res.BRCR_CHECK_AREA)

        self.AddUserArea(res.BRCR_SEND_AREA, c4d.BFH_SCALEFIT, inith=c4d.gui.SizePix(breadcrumb_indent + breadcrumb_h))
        self.AttachUserArea(self.ua_brcr_send, res.BRCR_SEND_AREA)
        self.GroupEnd()

        self.GroupBegin(id=res.GRP_TITLE, flags=c4d.BFH_SCALEFIT, inith=c4d.gui.SizePix(title_area_h))
        self.GroupBorderNoTitle(borderstyle=c4d.BORDER_NONE)
        area = self.AddUserArea(res.TITLE_AREA, c4d.BFH_SCALEFIT, inith=c4d.gui.SizePix(title_area_h))
        self.AttachUserArea(self.ua_title, area)
        self.GroupEnd()

        self.GroupBegin(id=res.GRP_DYNPAGE, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1)
        # self.GroupBorderNoTitle(borderstyle=c4d.BORDER_ACTIVE_4)
        # self.GroupBorderSpace(10, 10, 10, 10)
        self.page = 0
        self.page_collect()
        self.GroupEnd()

        self.GroupBegin(id=res.GRP_BACK_FOV, flags=c4d.BFV_BOTTOM | c4d.BFH_SCALEFIT, inith=25, rows=1, cols=3, title="",
                        groupflags=c4d.BORDER_GROUP_IN)
        self.GroupBorderNoTitle(borderstyle=c4d.BORDER_NONE)  # BORDER_NONE BORDER_BLACK
        self.GroupBorderSpace(70, 20, 70, 20)  # padding_bottom
        self.AddButton(res.BTN_PREV, flags=c4d.BFH_LEFT | c4d.BFV_SCALEFIT | c4d.BFH_SCALE, initw=200, inith=20, name="Back")
        self.AddButton(res.BTN_REFRESH, flags=c4d.BFH_CENTER | c4d.BFV_SCALEFIT | c4d.BFH_SCALE, initw=200, inith=20,
                       name="Refresh")
        self.AddButton(res.BTN_NEXT, flags=c4d.BFH_RIGHT | c4d.BFV_SCALEFIT | c4d.BFH_SCALE, initw=200, inith=20,
                       name="Next")
        self.GroupEnd()

        self.AddSeparatorH(initw=0, flags=c4d.BFH_SCALEFIT)
        self.GroupBegin(id=res.GRP_STATUS_BAR, flags=c4d.BFV_BOTTOM | c4d.BFH_SCALEFIT, groupflags=c4d.BORDER_GROUP_IN,
                        cols=1)
        self.GroupBorderNoTitle(borderstyle=c4d.BORDER_NONE)
        self.GroupBorderSpace(70, 0, 70, 5)
        self.AddStaticText(res.IDS_STATUS_BAR, c4d.BFH_SCALEFIT | c4d.BFH_LEFT)
        self.GroupEnd()

        self.set_status("default")

        self.GroupEnd()

        self.element_hide()
        return True

    def Command(self, id, msg):

        if id == res.BTN_CALC:
            webbrowser.open('http://lacrimasfarm.com/calc', new=2)

        if id == res.BTN_INSTRUCT:
            webbrowser.open('http://lacrimasfarm.com/cinema', new=2)

        if id == res.BTN_PREV:
            if self.page == 1:
                self.page = 0

            elif self.page == 2:
                self.page = 1
            self.set_page()

        if id == res.BTN_NEXT:
            if self.page == 0:
                proj_name = Utils.get_proj_name()
                if not proj_name:
                    self.set_status("proj_name")
                    return True
                translit_name = Utils.get_translit_name(proj_name)
                if proj_name != translit_name:
                    self.set_status("proj_name_translit")
                    return True
                else:
                    Utils.save_proj_path(self.GetString(res.EDS_PROJNAME))

                collect = self.worker.collect()
                if collect:
                    self.page = 1
                    self.set_page()

            elif self.page == 1:
                self.page = 2
                self.set_page()

            elif self.page == 2:
                if Utils.save_changes():
                    txt = "Scene successfully saved and ready to send."
                else:
                    txt = "Error occured! Scene not saved."
                c4d.gui.MessageDialog(txt)

        if id == res.BTN_REFRESH:
            if self.page == 1:
                self.page_check()
            elif self.page == 2:
                self.page_send()
            pass

        return True

    def Abort(self):
        return True

    def AskClose(self):
        print("CLOSE")
        self.Abort()  # Abort on close
        return False

    def searchNames(self, value):
        for k, v in c4d.__dict__.items():
            if v == value:
                yield k

    def CoreMessage(self, id, msg):
        if id == PLUGIN_ID:
            # Get the actual data (This is beyond my knowledge but it works!)
            P1MSG_UN = msg.GetVoid(c4d.BFM_CORE_PAR1)
            pythonapi.PyCapsule_GetPointer.restype = c_void_p
            pythonapi.PyCapsule_GetPointer.argtypes = [py_object]
            P1MSG_EN = pythonapi.PyCapsule_GetPointer(P1MSG_UN)

            if P1MSG_EN == MSG_CONSOLE:  # update console
                self.SetString(CONSOLE_AREA, self.console)

            return True

        return gui.GeDialog.CoreMessage(self, id, msg)

    def Message(self, msg, result):
        if msg.GetId() == c4d.BFM_ACTION:
            if msg[c4d.BFM_ACTION_ID] == res.EDS_PROJNAME:
                data = c4d.BaseContainer()
                data.SetString(1009, msg[c4d.BFM_ACTION_VALUE])
                c4d.plugins.SetWorldPluginData(PLUGIN_ID, data)

        if msg.GetId() == c4d.BFM_ADJUSTSIZE:
            # self.ua_title.Redraw()
            pass

        return gui.GeDialog.Message(self, msg, result)


def PluginMessage(id, data):
    if id == c4d.C4DPL_ENDACTIVITY:
        pass
        # print("C4D IS CLOSING")
    elif id == c4d.C4DPL_SYSTEM_SLEEP:
        pass
        # print("C4D IS SLEEP")
    elif id == c4d.C4DPL_SYSTEM_WAKE:
        pass
        # print("C4D IS WAKEUP")
    elif id == c4d.C4DPL_RELOADPYTHONPLUGINS:
        pass
        # print("PLUGINS RELOAD")


class Milker(c4d.plugins.CommandData):
    dialog = None

    def Register(self):
        return c4d.plugins.RegisterCommandPlugin(
            PLUGIN_ID, PLUGIN_NAME, PLUGIN_INFO, PLUGIN_ICON,
            PLUGIN_HELP, self)

    def Execute(self, doc):
        # print("EXECUTE")
        if self.dialog is None:
            self.dialog = LACRIMASDialog()
        return self.dialog.Open(dlgtype=c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID, xpos=-2, ypos=-2, defaulth=950, defaultw=800)

    def RestoreLayout(self, sec_ref):
        # print("RESTORE")
        if self.dialog is None:
            self.dialog = LACRIMASDialog()

        return self.dialog.Restore(pluginid=PLUGIN_ID, secret=sec_ref)


if __name__ == '__main__':
    Milker().Register()
