import hou


def _light_deleted(event_type, **kwargs):
    child_node = kwargs['child_node']
    child_node_name = child_node.name()
    target_node = child_node.parent().parent()
    tgt_ptg = target_node.parmTemplateGroup()
    tgt_mod_folder = _get_modify_folder(group=tgt_ptg)
    new_tgt_mod_f = tgt_mod_folder.clone()
    new_tgt_mod_f_pts = new_tgt_mod_f.parmTemplates()
    new_pts_list = [x for x in new_tgt_mod_f_pts if x.label() != child_node_name]
    new_tgt_mod_f.setParmTemplates(new_pts_list)
    tgt_ptg.replace(tgt_mod_folder, new_tgt_mod_f)
    target_node.setParmTemplateGroup(tgt_ptg)
    print(f'light {child_node_name} deleted')

def _rename_parm_templates(src_node_name, src_pts):
    src_pts_list = list(src_pts)
    for parm_template in src_pts_list:
        pt_name = parm_template.name()
        parm_template.setName(src_node_name.lower() + '_' + pt_name)
    pts = tuple(src_pts_list)
    return pts


def _create_folder_parm_template(source_node_name, source_fpt):
    """
    Creates a hou.FolderParmTemplate object for the target node.
    :param source_node_name: the hou.Node parameters come from
    :param source_fpt: tuple of hou.ParmTemplate objects
    :return: ready to insertion hou.FolderParmTemplate object
    """
    fpt_name = 'pr_' + source_node_name.lower()

    fpt = hou.FolderParmTemplate(name=fpt_name,
                                 label=source_node_name,
                                 parm_templates=source_fpt,
                                 folder_type=hou.folderType.Tabs)
    return fpt


def create_arnold_light(light_type):
    asset_node = hou.pwd()
    lights_node = asset_node.node("lights")
    current_light = lights_node.createNode("arnold_light")
    copy_parms_templates(node=current_light)
    current_light.setParms({"ar_light_type": light_type})
    asset_node.setParms({f"{current_light.name().lower()}_ar_light_type": light_type})
    if light_type == 'skydome':
        current_light.setParms({"ar_light_color_type": 'texture'})
        current_light.setParms({"ar_format": 'latlong'})
        asset_node.setParms({f"{current_light.name().lower()}_ar_light_color_type": 'texture'})
        asset_node.setParms({f"{current_light.name().lower()}_ar_format": 'latlong'})
    reference_parms(node=current_light)


def _get_modify_folder(group):
    lights_f = group.findFolder('Lights')
    lights_f_pts = lights_f.parmTemplates()
    for pt in lights_f_pts:
        if pt.label() == 'Modify':
            return pt


def copy_parms_templates(node):
    # list of hou.FolderParmTemplate objects
    _fpts = []
    # target_node = kwargs['node']
    target_node = hou.pwd()
    source_node = node
    # get hou.ParmTemplateGroup() objects for the target and source nodes
    target_group = target_node.parmTemplateGroup()
    source_group = source_node.parmTemplateGroup()
    # get the "Modify" folder's hou.FolderParmTemplate object on target node
    target_modify_folder = _get_modify_folder(group=target_group)
    # get the source_node's name
    source_node_name = source_node.name()
    # loop over hou.FolderParmTemplate objects on the source node
    for entry in source_group.entries():
        # take into account only visible folders
        if entry.type() == hou.parmTemplateType.Folder and not entry.isHidden():
            source_node_folder_name = entry.label()
            parm_templates = entry.parmTemplates()
            # loop over hou.ParmTemplate objects inside folder
            for parm_template in parm_templates:
                pt_name = parm_template.name()
                pt_callback = parm_template.scriptCallback()
                # check if String Parameter contains custom made menu and get its script and then change it
                if parm_template.type() == hou.parmTemplateType.String:
                    menu_script = parm_template.itemGeneratorScript()
                    if len(menu_script) > 0:
                        new_menu_script = menu_script.replace('ar_', f'{source_node_name}_ar_')
                        parm_template.setItemGeneratorScript(new_menu_script)
                # change the node object in the parameter's callback script field
                if len(pt_callback) > 0:
                    modified_callback = pt_callback.replace("kwargs['node']", f"hou.node('{source_node.path()}')")
                    parm_template.setScriptCallback(modified_callback)
                # change conditions in parameter's "Disable When" and "Hide When" fields
                for key, value in parm_template.conditionals().items():
                    if str(key) == 'parmCondType.DisableWhen':
                        new_condition = value.replace(" ar_", f" {source_node_name}_ar_")
                        new_condition = new_condition.replace(" light_enable", f" {source_node_name}_light_enable")
                        parm_template.setConditional(hou.parmCondType.DisableWhen, new_condition)
                    if str(key) == 'parmCondType.HideWhen':
                        new_condition = value.replace(" ar_", f" {source_node_name}_ar_")
                        parm_template.setConditional(hou.parmCondType.HideWhen, new_condition)
                # rename the hou.ParmTemplate object
                parm_template.setName(source_node_name.lower() + '_' + pt_name)
            # create a hou.FolderParmTemplate object from the modified copies of hou.ParmTemplate objects
            # and then append it to the list of folders to place in target's node interface
            _fpts.append(_create_folder_parm_template(source_node_name=source_node_folder_name,
                                                      source_fpt=parm_templates))
    # create a grouped hou.FolderParmTemplate for the particular source node in target node's interface
    fpt_for_the_node = _create_folder_parm_template(source_node_name=source_node_name,
                                                    source_fpt=_fpts)
    # add the created hou.FolderParmTemplate object to the 'Modify`s' hou.FolderParmTemplate object
    new_target_modify_folder = target_modify_folder.clone()
    new_target_modify_folder.addParmTemplate(fpt_for_the_node)
    # replace an old modify folder with a new one
    target_group.replace(target_modify_folder, new_target_modify_folder)
    # apply all changes
    target_node.setParmTemplateGroup(target_group)


def reference_parms(node):
    asset_node = hou.pwd()
    light_node_name = node.name()
    parmtuples_tuple = node.parmTuples()
    for parmtuple in parmtuples_tuple:
        node.parmTuple(parmtuple.name()).set(asset_node.parmTuple(f'{light_node_name.lower()}_{parmtuple.name()}'))

