kwargs['node'].node('lights').addEventCallback((hou.nodeEventType.ChildDeleted, ), kwargs['node'].hdaModule()._light_deleted)
print("Callbacks added")
