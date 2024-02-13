# -*- coding: utf-8 -*-

from pyrevit import revit, DB, script, forms, HOST_APP, coreutils, PyRevitException
from pyrevit.framework import List
from collections import defaultdict
from pychilizer import units
from pyrevit.revit.db import query
from Autodesk.Revit import Exceptions
import clr
import System



BIC = DB.BuiltInCategory

def get_alphabetic_labels(nr):
    # get N letters A, B, C, etc or AA, AB, AC if N more than 26
    alphabet = [chr(i) for i in range(65, 91)]
    double_alphabet = []
    for i in range(26):
        c1 = alphabet[i]
        for j in range(26):
            c2 = alphabet[j]
            l = c1 + c2
            double_alphabet.append(l)
    labels = []
    if nr <= 26:
        labels = alphabet[:nr]
    elif nr > 26:
        labels = double_alphabet[:nr]
    return labels


def any_fill_type(doc=revit.doc):
    # get any Filled Region Type
    return DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType).FirstElement()


def invis_style(doc=revit.doc):
    # get invisible lines graphics style
    for gs in DB.FilteredElementCollector(doc).OfClass(DB.GraphicsStyle):
        # find style using the category Id
        if gs.GraphicsStyleCategory.Id.IntegerValue == -2000064:
            return gs


def get_sheet(some_number, doc=revit.doc):
    sheet_nr_filter = get_biparam_stringequals_filter({DB.BuiltInParameter.SHEET_NUMBER: str(some_number)})
    found_sheet = DB.FilteredElementCollector(doc) \
        .OfCategory(DB.BuiltInCategory.OST_Sheets) \
        .WherePasses(sheet_nr_filter) \
        .WhereElementIsNotElementType().ToElements()

    return found_sheet


def get_biparam_stringequals_filter(bip_paramvalue_dict):
    # copy of the pyrevit query def, updated to R2023
    filters = []
    for bip, fvalue in bip_paramvalue_dict.items():
        bip_id = DB.ElementId(bip)
        bip_valueprovider = DB.ParameterValueProvider(bip_id)
        if HOST_APP.is_newer_than(2022):
            bip_valuerule = DB.FilterStringRule(bip_valueprovider,
                                                DB.FilterStringEquals(),
                                                fvalue)
        else:
            bip_valuerule = DB.FilterStringRule(bip_valueprovider,
                                                DB.FilterStringEquals(),
                                                fvalue,
                                                True)
        filters.append(bip_valuerule)

    if filters:
        return DB.ElementParameterFilter(
            List[DB.FilterRule](filters)
        )
    else:
        raise PyRevitException('Error creating filters.')


def get_view(some_name, doc=revit.doc):
    view_name_filter = get_biparam_stringequals_filter({DB.BuiltInParameter.VIEW_NAME: some_name})
    found_view = DB.FilteredElementCollector(doc) \
        .OfCategory(DB.BuiltInCategory.OST_Views) \
        .WherePasses(view_name_filter) \
        .WhereElementIsNotElementType().ToElements()

    return found_view


def get_fam_types(family_name, doc=revit.doc):
    fam_bip_id = DB.ElementId(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
    fam_bip_provider = DB.ParameterValueProvider(fam_bip_id)
    if HOST_APP.is_newer_than(2022):
        fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), family_name)
    else:
        fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), family_name, True)
    fam_filter = DB.ElementParameterFilter(fam_filter_rule)

    collector = DB.FilteredElementCollector(doc) \
        .WherePasses(fam_filter) \
        .WhereElementIsElementType()

    return collector


def get_fam_any_type(family_name, doc=revit.doc):
    fam_bip_id = DB.ElementId(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
    fam_bip_provider = DB.ParameterValueProvider(fam_bip_id)
    if HOST_APP.is_newer_than(2022):
        fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), family_name)
    else:
        fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), family_name, True)
    fam_filter = DB.ElementParameterFilter(fam_filter_rule)

    collector = DB.FilteredElementCollector(doc) \
        .WherePasses(fam_filter) \
        .WhereElementIsElementType() \
        .FirstElement()

    return collector


def get_solid_fill_pat(doc=revit.doc):
    # get fill pattern element Solid Fill
    # updated to work in other languages
    fill_pats = DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement)
    solid_pat = [pat for pat in fill_pats if pat.GetFillPattern().IsSolidFill]
    return solid_pat[0]


def param_set_by_cat(cat, doc=revit.doc):
    # get all project type parameters of a given category
    # can be used to gather parameters for UI selection
    all_gm = DB.FilteredElementCollector(doc).OfCategory(cat).WhereElementIsElementType().ToElements()
    parameter_set = []
    for gm in all_gm:
        params = gm.Parameters
        for p in params:
            if p not in parameter_set and p.IsReadOnly == False:
                parameter_set.append(p)
    return parameter_set


def add_material_parameter(family_document, parameter_name, is_instance):
    # add a material parameter to the family doc
    if HOST_APP.is_newer_than(2021):
        return family_document.FamilyManager.AddParameter(parameter_name,
                                                          DB.GroupTypeId.Materials,
                                                          DB.SpecTypeId.Reference.Material,
                                                          is_instance)
    else:
        return family_document.FamilyManager.AddParameter(parameter_name,
                                                          DB.BuiltInParameterGroup.PG_MATERIALS,
                                                          DB.ParameterType.Material,
                                                          is_instance)



def create_sheet(sheet_num, sheet_name, titleblock, doc=revit.doc):
    sheet_num = str(sheet_num)

    new_datasheet = DB.ViewSheet.Create(doc, titleblock)
    new_datasheet.Name = sheet_name

    while get_sheet(sheet_num):
        sheet_num = coreutils.increment_str(sheet_num, 1)
    new_datasheet.SheetNumber = str(sheet_num)

    return new_datasheet


def set_anno_crop(v):
    anno_crop = v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
    anno_crop.Set(1)
    return anno_crop


def apply_vt(v, vt):
    if vt:
        v.ViewTemplateId = vt.Id
    return


def get_name(el):
    return DB.Element.Name.__get__(el)


def create_parallel_bbox(line, crop_elem, offset=300 / 304.8):
    # create section parallel to x (solution by Building Coder)
    p = line.GetEndPoint(0)
    q = line.GetEndPoint(1)
    v = q - p

    # section box width
    w = v.GetLength()
    bb = crop_elem.get_BoundingBox(None)
    minZ = bb.Min.Z
    maxZ = bb.Max.Z
    # height = maxZ - minZ

    min = DB.XYZ(-w, minZ - offset, -offset)
    max = DB.XYZ(w, maxZ + offset, offset)

    centerpoint = p + 0.5 * v
    direction = v.Normalize()
    up = DB.XYZ.BasisZ
    view_direction = direction.CrossProduct(up)

    t = DB.Transform.Identity
    t.Origin = centerpoint
    t.BasisX = direction
    t.BasisY = up
    t.BasisZ = view_direction

    section_box = DB.BoundingBoxXYZ()
    section_box.Transform = t
    section_box.Min = min
    section_box.Max = max

    pt = DB.XYZ(centerpoint.X, centerpoint.Y, minZ)
    point_in_front = pt + (-3) * view_direction
    # TODO: check other usage
    return section_box


def char_series(nr):
    from string import ascii_uppercase
    series = []
    for i in range(0, nr):
        series.append(ascii_uppercase[i])
    return series


def char_i(i):
    from string import ascii_uppercase
    return ascii_uppercase[i]


def get_view_family_types(viewtype, doc):
    return [vt for vt in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if
            vt.ViewFamily == viewtype]


def get_family_template_path():
    return __revit__.Application.FamilyTemplatePath


def get_family_template_language():
    family_template_path = get_family_template_path()
    template_language = family_template_path.split("\\")[-1]
    return template_language


def fam_template_name_by_lang_and_cat(language, category_id):
    # matching the template to category Id in several languages
    temp_dict_eng = defaultdict(lambda: None, {
        -2001000: "\Metric Casework.rft",
        -2000080: "\Metric Furniture.rft",
        -2001040: "\Metric Electrical Equipment.rft",
        -2001370: "\Metric Entourage.rft",
        -2001100: "\Metric Furniture System.rft",
        -2001120: "\Metric Lighting Fixture.rft",
        -2001140: "\Metric Mechanical Equipment.rft",
        -2001180: "\Metric Parking.rft",
        -2001360: "\Metric Planting.rft",
        -2001160: "\Metric Plumbing Fixture.rft",
        -2001260: "\Metric Site.rft",
        -2001350: "\Metric Specialty Equipment.rft",
    })
    temp_dict_eng_i = defaultdict(lambda: None, {
        -2001000: "\Casework.rft",
        -2000080: "\Furniture.rft",
        -2001040: "\Electrical Equipment.rft",
        -2001370: "\Entourage.rft",
        -2001100: "\Furniture System.rft",
        -2001120: "\Lighting Fixture.rft",
        -2001140: "\Mechanical Equipment.rft",
        -2001180: "\Parking.rft",
        -2001360: "\Planting.rft",
        -2001160: "\Plumbing Fixture.rft",
        -2001260: "\Site.rft",
        -2001350: "\Specialty Equipment.rft",
    })
    temp_dict_fra = defaultdict(lambda: None, {
        -2001000: "\Meubles de rangement métriques.rft",
        -2000080: "\Mobilier métrique.rft",
        -2001040: "\Equipement électrique métrique.rft",
        -2001370: "\Environnement métrique.rft",
        -2001100: "\Système de mobilier métrique.rft",
        -2001120: "\Luminaires métriques.rft",
        -2001140: "\Equipement mécanique métrique.rft",
        -2001180: "\Parking métrique.rft",
        -2001360: "\Plantes métriques.rft",
        -2001160: "\Installations de plomberie métriques.rft",
        -2001260: "\Site métrique.rft",
        -2001350: "\Equipement spécialisé métrique.rft",
    })
    temp_dict_deu = defaultdict(lambda: None, {
        -2001040: "\Elektrogeräte.rft",
        -2001120: "\Leuchten.rft",
        -2001140: "\Mechanische Geräte.rft",
        -2001360: "\Bepflanzung.rft",
        -2001160: "\Sanitärinstallation.rft",
    })

    if language == "English":
        return temp_dict_eng[category_id]
    elif language == "English_I" or language == "English-Imperial":
        return temp_dict_eng_i[category_id]
    elif language == "French":
        return temp_dict_fra[category_id]
    elif language == "German":
        return temp_dict_deu[category_id]
    else:
        return None


def get_generic_family_template_name():
    # get the name of the generic model template

    ENG = "\Metric Generic Model.rft"
    ENG_I = "\Generic Model.rft"
    FRA = "\Modèle générique métrique.rft"
    GER = "\Allgemeines Modell.rft"
    ESP = "\Modelo genérico métrico.rft"
    RUS = "\Метрическая система, типовая модель.rft"
    CHN = "\基于两个标高的公制常规模型.rft"
    ITA = "\Modello generico metrico.rft"
    JPN = "\一般モデル(メートル単位).rft"
    PLK = "\Model ogólny (metryczny).rft"
    CSY = "\Obecný model.rft"
    PTB = "\Modelo genérico métrico.rft"
    KOR = "\미터법 일반 모델.rft"

    template_language = get_family_template_language()
    if ("English_I") in template_language or ("English-I") in template_language:
        return ENG_I
    elif ("English") in template_language:
        return ENG
    elif ("French") in template_language:
        return FRA
    elif ("Spanish") in template_language:
        return ESP
    elif ("German") in template_language:
        return GER
    elif ("Russian") in template_language:
        return RUS
    elif ("Chinese") in template_language:
        return CHN
    elif ("Czech") in template_language:
        return CSY
    elif ("Italian") in template_language:
        return ITA
    elif ("Japanese") in template_language:
        return JPN
    elif ("Korean") in template_language:
        return KOR
    elif ("Polish") in template_language:
        return PLK
    elif ("Portuguese") in template_language:
        return PTB
    else:
        return None



def get_mass_template_path():
    fam_template_folder = __revit__.Application.FamilyTemplatePath

    ENG = "\Conceptual Mass\Metric Mass.rft"
    FRA = "\Volume conceptuel\Volume métrique.rft"
    GER = "\Entwurfskörper\Entwurfskörper.rft"
    ESP = "\Masas conceptuales\Masa métrica.rft"
    RUS = "\Концептуальные формы\Метрическая система, формообразующий элемент.rft"

    if ("French") in fam_template_folder:
        mass_temp_name = FRA
    elif ("Spanish") in fam_template_folder:
        mass_temp_name = ESP
    elif ("German") in fam_template_folder:
        mass_temp_name = GER
    elif ("Russian") in fam_template_folder:
        mass_temp_name = RUS
    else:
        mass_temp_name = ENG

    mass_template_path = fam_template_folder + mass_temp_name
    from os.path import isfile
    if isfile(mass_template_path):
        return mass_template_path
    else:
        forms.alert(title="No Mass Template Found",
                    msg="There is no Mass Model Template in the default location. Can you point where to get it?",
                    ok=True)
        fam_template_path = forms.pick_file(file_ext="rft",
                                            init_dir="C:\ProgramData\Autodesk\RVT " + HOST_APP.version + "\Family Templates")
        return fam_template_path


def vt_name_match(vt_name, doc=revit.doc):
    # return a view template with a given name, None if not found
    views = DB.FilteredElementCollector(doc).OfClass(DB.View)
    vt_match = None
    for v in views:
        if v.IsTemplate and v.Name == vt_name:
            vt_match = v.Name
    return vt_match


def vp_name_match(vp_name, doc=revit.doc):
    # return a view template with a given name, None if not found
    views = DB.FilteredElementCollector(doc).OfClass(DB.Viewport)
    # if no viewports exist:
    if not views.ToElements():
        return None
    for v in views:
        if v.Name == vp_name:
            return v.Name
    return views.FirstElement().Name


def tb_name_match(tb_name, doc=revit.doc):
    titleblocks = DB.FilteredElementCollector(doc).OfCategory(
        DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType()
    for tb in titleblocks:
        fam_name = tb.Family.Name
        type_name = get_name(tb)
        joined_name = fam_name + " : " + type_name
        if joined_name == tb_name:
            return joined_name


def unique_view_name(name, suffix=None):
    unique_v_name = name + suffix
    while get_view(unique_v_name):
        unique_v_name = unique_v_name + " Copy 1"
    return unique_v_name


def shift_list(l, n):
    return l[n:] + l[:n]


def get_viewport_types(doc=revit.doc):
    # get viewport types using a parameter filter
    bip_id = DB.ElementId(DB.BuiltInParameter.VIEWPORT_ATTR_SHOW_LABEL)
    bip_provider = DB.ParameterValueProvider(bip_id)
    rule = DB.FilterIntegerRule(bip_provider, DB.FilterNumericGreaterOrEqual(), 0)
    param_filter = DB.ElementParameterFilter(rule)

    collector = DB.FilteredElementCollector(doc) \
        .WherePasses(param_filter) \
        .WhereElementIsElementType() \
        .ToElements()

    return collector


def get_vp_by_name(name, doc=revit.doc):
    #
    bip_id = DB.ElementId(DB.BuiltInParameter.VIEWPORT_ATTR_SHOW_LABEL)
    bip_provider = DB.ParameterValueProvider(bip_id)
    rule = DB.FilterIntegerRule(bip_provider, DB.FilterNumericGreaterOrEqual(), 0)
    param_filter = DB.ElementParameterFilter(rule)

    type_bip_id = DB.ElementId(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
    type_bip_provider = DB.ParameterValueProvider(type_bip_id)
    if HOST_APP.is_newer_than(2022):
        type_filter_rule = DB.FilterStringRule(type_bip_provider, DB.FilterStringEquals(), name)
    else:
        type_filter_rule = DB.FilterStringRule(type_bip_provider, DB.FilterStringEquals(), name, True)
    type_filter = DB.ElementParameterFilter(type_filter_rule)

    and_filter = DB.LogicalAndFilter(param_filter, type_filter)

    collector = DB.FilteredElementCollector(doc) \
        .WherePasses(and_filter) \
        .WhereElementIsElementType() \
        .FirstElement()

    return collector


def get_3Dviewtype_id(doc=revit.doc):
    view_fam_type = DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
    return next(vt.Id for vt in view_fam_type if vt.ViewFamily == DB.ViewFamily.ThreeDimensional)


def delete_existing_view(view_name, doc=revit.doc):
    for view in DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements():
        if view.Name == view_name:
            try:
                doc.Delete(view.Id)
                break
            except:

                forms.alert('Current view was cannot be deleted. Close view and try again.')
                return False
    return True


def remove_viewtemplate(vt_id, doc=revit.doc):
    viewtype = doc.GetElement(vt_id)
    template_id = viewtype.DefaultTemplateId
    if template_id.IntegerValue != -1:
        if forms.alert(
                "You are about to remove the View Template"
                " associated with this View Type. Is that cool with ya?",
                ok=False, yes=True, no=True, exitscript=True):
            viewtype.DefaultTemplateId = DB.ElementId(-1)


def family_and_type_names(elem, doc):
    fam_name = doc.GetElement(elem.GetTypeId()).FamilyName
    type_name = get_name(elem)
    return (" - ".join([fam_name, type_name]))


def create_filter_from_rules(rules):
    elem_filters = List[DB.ElementFilter]()
    for rule in rules:
        elem_param_filter = DB.ElementParameterFilter(rule)
        elem_filters.Add(elem_param_filter)
    el_filter = DB.LogicalAndFilter(elem_filters)
    return el_filter


def check_filter_exists(filter_name, doc=revit.doc):
    all_view_filters = DB.FilteredElementCollector(doc).OfClass(DB.FilterElement).ToElements()

    for vf in all_view_filters:
        if filter_name == str(vf.Name):
            return vf


def create_filter(filter_name, bics_list, doc=revit.doc):
    cat_list = List[DB.ElementId](DB.ElementId(cat) for cat in bics_list)
    filter = DB.ParameterFilterElement.Create(doc, filter_name, cat_list)
    return filter


def filter_from_rules(rules, or_rule=False):
    elem_filters = List[DB.ElementFilter]()
    for rule in rules:
        elem_parameter_filter = DB.ElementParameterFilter(rule)
        elem_filters.Add(elem_parameter_filter)
    if or_rule:
        elem_filter = DB.LogicalOrFilter(elem_filters)
    else:
        elem_filter = DB.LogicalAndFilter(elem_filters)
    return elem_filter


def get_param_value_as_string(p):
    # get the value of the element paramter as a string, regardless of the storage type

    if p.HasValue:
        if p_storage_type(p) == "ElementId":
            if p.Definition.Name == "Category":

                return p.AsValueString()
            else:
                return p.AsElementId().IntegerValue
        elif p_storage_type(p) == "Integer":

            return p.AsInteger()
        elif p_storage_type(p) == "Double":

            return p.AsValueString()
        elif p_storage_type(p) == "String":

            return p.AsString()
    else:
        return

def get_param_value_by_storage_type(p):
    # get the value of the element parameter by storage type

    if p.HasValue:
        if p_storage_type(p) == "ElementId":
            return p.AsElementId()
        elif p_storage_type(p) == "Integer":
            return p.AsInteger()
        elif p_storage_type(p) == "Double":
            return p.AsDouble()
        elif p_storage_type(p) == "String":
            return p.AsString()
    else:
        return


def p_storage_type(param):
    return param.StorageType.ToString()


def get_parameter_from_name(el, param_name):
    params = el.Parameters
    for p in params:
        if p.Definition.Name == param_name:
            return p


def get_builtin_label(bip_or_bic):
    # returns a language-specific label for the bip or bic
    return DB.LabelUtils.GetLabelFor(bip_or_bic)

def create_filter_by_name_bics(filter_name, bics_list, doc=revit.doc):
    cat_list = List[DB.ElementId](DB.ElementId(cat) for cat in bics_list)
    filter = DB.ParameterFilterElement.Create(doc, filter_name, cat_list)
    return filter

def shared_param_id_from_guid(categories_list, guid, doc=revit.doc):
    # from the GUID, return the id of the shared parameter
    for bic in categories_list:
        # iterating through each category helps address cases where some selected categories are not present in the model
        any_element_of_cat = DB.FilteredElementCollector(doc).OfCategory(
            bic).WhereElementIsNotElementType().ToElements()
        for el in any_element_of_cat:
            element_i_params = el.Parameters
            for p in element_i_params:
                try:
                    if p.GUID == guid:
                        return p.Id
                except Exceptions.InvalidOperationException:
                    pass
            element_t_params = query.get_type(el).Parameters
            for p in element_t_params:
                try:
                    if p.GUID and p.GUID == guid:
                        return p.Id
                except Exceptions.InvalidOperationException:
                    pass
    return None

def get_document_model_bics(doc=revit.doc):
    # get all model builtin categories of the doc
    built_in_categories = []
    for category in doc.Settings.Categories:
        if HOST_APP.is_newer_than(2022):
            bic = category.BuiltInCategory
        else:
            bic = System.Enum.ToObject(BIC, category.Id.IntegerValue)
            # print (type(bic), bic)
        if category.CategoryType==DB.CategoryType.Model and bic!= DB.BuiltInCategory.INVALID and category.Id.IntegerValue <0:
            built_in_categories.append(bic)
    return built_in_categories


FREQUENTLY_SELECTED_CATEGORIES=[
        BIC.OST_Casework,
        BIC.OST_Ceilings,
        BIC.OST_Columns,
        BIC.OST_Floors,
        BIC.OST_GenericModel,
        BIC.OST_PlumbingFixtures,
        BIC.OST_Walls,
        BIC.OST_Windows,
        ]

def frequent_category_labels():
    return [get_builtin_label(bic) for bic in FREQUENTLY_SELECTED_CATEGORIES]


def model_categories_dict(doc):
    # a dictionary of common categories used for colorizers
    # formatted as {Category name : BIC}
    category_opt_dict = {}
    for cat in get_document_model_bics(doc):
        category_opt_dict[get_builtin_label(cat)] = cat
    return category_opt_dict


def category_labels_to_bic(labels, doc):
    categories_dict = {}
    for label in labels:
        categories_dict[label]=model_categories_dict(doc)[label]
    return categories_dict
