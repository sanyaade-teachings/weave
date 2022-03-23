from .. import panel
from .. import graph
from .. import weave_types as types
from ..api import op, mutation, weave_class
from ..weave_internal import make_var_node


class PanelType(types.ObjectType):
    name = "panel_type"

    type_vars = {}

    def __init__(self):
        pass

    def property_types(self):
        return {
            "id": types.String(),
            "input_node": types.Function(types.TypedDict({}), types.Any()),
            "config": types.Any(),
        }


class SliderConfigType(types.ObjectType):
    name = "slider_config_type"

    type_vars = {}

    def __init__(self):
        pass

    def property_types(self):
        return {
            "min": types.Int(),
            "max": types.Int(),
            "step": types.Int(),
        }


@weave_class(weave_type=SliderConfigType)
class SliderConfig:
    def __init__(self, min, max, step):
        self.min = min
        self.max = max
        self.step = step


SliderConfigType.instance_classes = SliderConfig
SliderConfigType.instance_class = SliderConfig


class SliderPanelType(types.ObjectType):
    name = "slider_panel_type"

    type_vars = {}

    def __init__(self):
        pass

    def property_types(self):
        return {
            "id": types.ConstString("slider"),
            "input_node": types.Function(types.TypedDict({}), types.Number()),
            "config": SliderConfigType(),
        }


class Slider(panel.Panel):
    def __init__(self, id="slider", input_node=graph.VoidNode(), config=None):
        self.id = "slider"
        self.input_node = input_node
        self.config = config
        if self.config is None:
            self.config = SliderConfig(0, 100, 1)

    @op(
        name="sliderpanel-config",
        input_type={
            "self": SliderPanelType(),
        },
        output_type=SliderConfigType(),
    )
    def panel_config(self):
        return self.config


SliderPanelType.instance_classes = Slider
SliderPanelType.instance_class = Slider


class NumberPanelType(types.ObjectType):
    name = "number_panel_type"

    type_vars = {}

    def __init__(self):
        pass

    def property_types(self):
        return {
            "id": types.ConstString("number"),
            "input_node": types.Function(types.TypedDict({}), types.Number()),
            "config": types.TypedDict({}),
        }


class Number(panel.Panel):
    def __init__(self, id="number", input_node=graph.VoidNode(), config=None):
        self.id = "number"
        self.input_node = input_node
        self.config = {}


NumberPanelType.instance_classes = Number
NumberPanelType.instance_class = Number


class ContainerConfigType(types.ObjectType):
    name = "container_config_type"

    type_vars = {"variables": types.TypedDict({}), "panels": types.List(PanelType())}

    def __init__(self, variables, panels):
        self.variables = variables
        self.panels = panels

    def property_types(self):
        return {"variables": self.variables, "panels": self.panels}


class ContainerConfig:
    def __init__(self, variables={}, panels=[]):
        self.variables = variables
        self.panels = panels

    def add_variable(self, name, type, value):
        self.variables[name] = value
        return make_var_node(type, name)

    def add_panel(self, panel):
        self.panels.append(panel)

    @mutation
    def set_variables(self, variables):
        self.variables = variables
        return self

    @op(
        setter=set_variables,
        name="panelContainerConfig-variables",
        input_type={
            "self": ContainerConfigType(types.Any(), types.Any()),
        },
        output_type=types.TypedDict({}),
    )
    def config_variables(self):
        return self.variables

    @op(
        name="panelContainerConfig-panels",
        input_type={
            "self": ContainerConfigType(types.Any(), types.Any()),
        },
        output_type=types.List(PanelType()),
    )
    def config_panels(self):
        return self.panels


ContainerConfigType.instance_classes = ContainerConfig
ContainerConfigType.instance_class = ContainerConfig


class ContainerPanelType(types.ObjectType):
    name = "container_panel_type"

    type_vars = {
        "config": ContainerConfigType(types.TypedDict({}), types.List(PanelType()))
    }

    def __init__(self, config):
        self.config = config

    def property_types(self):
        return {"id": types.ConstString("container"), "config": self.config}


class Container(panel.Panel):
    def __init__(self, id="container", input_node=graph.VoidNode(), config=None):
        self.id = "container"
        self.input_node = graph.VoidNode()
        self.config = config
        if self.config is None:
            self.config = ContainerConfig()

    @mutation
    def set_config(self, config):
        self.config = config
        return self

    @op(
        setter=set_config,
        name="containerpanel-config",
        input_type={
            "self": ContainerPanelType(ContainerConfigType(types.Any(), types.Any())),
        },
        output_type=ContainerConfigType(types.Any(), types.Any()),
    )
    def panel_config(self):
        return self.config


ContainerPanelType.instance_classes = Container
ContainerPanelType.instance_class = Container
