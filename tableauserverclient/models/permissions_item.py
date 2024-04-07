import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

from defusedxml.ElementTree import fromstring

from .exceptions import UnknownGranteeTypeError, UnpopulatedPropertyError
from .group_item import GroupItem
from .reference_item import ResourceReference
from .user_item import UserItem

from tableauserverclient.helpers.logging import logger


class Permission:
    class Mode:
        Allow = "Allow"
        Deny = "Deny"

        def __repr__(self):
            return "<Enum Mode: Allow | Deny>"

    class Capability:
        AddComment = "AddComment"
        ChangeHierarchy = "ChangeHierarchy"
        ChangePermissions = "ChangePermissions"
        Connect = "Connect"
        Delete = "Delete"
        Execute = "Execute"
        ExportData = "ExportData"
        ExportImage = "ExportImage"
        ExportXml = "ExportXml"
        Filter = "Filter"
        ProjectLeader = "ProjectLeader"
        Read = "Read"
        ShareView = "ShareView"
        ViewComments = "ViewComments"
        ViewUnderlyingData = "ViewUnderlyingData"
        WebAuthoring = "WebAuthoring"
        Write = "Write"
        RunExplainData = "RunExplainData"
        CreateRefreshMetrics = "CreateRefreshMetrics"
        SaveAs = "SaveAs"

        def __repr__(self):
            return "<Enum Capability: AddComment | ChangeHierarchy | ChangePermission ... (17 more) >"


class PermissionsRule(object):
    def __init__(self, grantee: ResourceReference, capabilities: Dict[str, str]) -> None:
        self.grantee = grantee
        self.capabilities = capabilities

    def __repr__(self):
        return "<PermissionsRule grantee={}, capabilities={}>".format(self.grantee, self.capabilities)

    def __and__(self, other: "PermissionsRule") -> "PermissionsRule":
        if self.grantee != other.grantee:
            raise ValueError("Cannot AND two permissions rules with different grantees")
        capabilities = set((*self.capabilities.keys(), *other.capabilities.keys()))
        new_capabilities = {}
        for capability in capabilities:
            if (self.capabilities.get(capability), other.capabilities.get(capability)) == (Permission.Mode.Allow, Permission.Mode.Allow):
                new_capabilities[capability] = Permission.Mode.Allow
            elif Permission.Mode.Deny in (self.capabilities.get(capability), other.capabilities.get(capability)):
                new_capabilities[capability] = Permission.Mode.Deny

        return PermissionsRule(self.grantee, new_capabilities)

    def __or__(self, other: "PermissionsRule") -> "PermissionsRule":
        if self.grantee != other.grantee:
            raise ValueError("Cannot AND two permissions rules with different grantees")
        capabilities = set((*self.capabilities.keys(), *other.capabilities.keys()))
        new_capabilities = {}
        for capability in capabilities:
            if Permission.Mode.Allow in (self.capabilities.get(capability), other.capabilities.get(capability)):
                new_capabilities[capability] = Permission.Mode.Allow
            elif (self.capabilities.get(capability), other.capabilities.get(capability)) == (Permission.Mode.Deny, Permission.Mode.Deny):
                new_capabilities[capability] = Permission.Mode.Deny

        return PermissionsRule(self.grantee, new_capabilities)

    @classmethod
    def from_response(cls, resp, ns=None) -> List["PermissionsRule"]:
        parsed_response = fromstring(resp)

        rules = []
        permissions_rules_list_xml = parsed_response.findall(".//t:granteeCapabilities", namespaces=ns)

        for grantee_capability_xml in permissions_rules_list_xml:
            capability_dict: Dict[str, str] = {}

            grantee = PermissionsRule._parse_grantee_element(grantee_capability_xml, ns)

            for capability_xml in grantee_capability_xml.findall(".//t:capabilities/t:capability", namespaces=ns):
                name = capability_xml.get("name")
                mode = capability_xml.get("mode")

                if name is None or mode is None:
                    logger.error("Capability was not valid: {}".format(capability_xml))
                    raise UnpopulatedPropertyError()
                else:
                    capability_dict[name] = mode

            rule = PermissionsRule(grantee, capability_dict)
            rules.append(rule)

        return rules

    @staticmethod
    def _parse_grantee_element(grantee_capability_xml: ET.Element, ns: Optional[Dict[str, str]]) -> ResourceReference:
        """Use Xpath magic and some string splitting to get the right object type from the xml"""

        # Get the first element in the tree with an 'id' attribute
        grantee_element = grantee_capability_xml.findall(".//*[@id]", namespaces=ns).pop()
        grantee_id = grantee_element.get("id", None)
        grantee_type = grantee_element.tag.split("}").pop()

        if grantee_id is None:
            logger.error("Cannot find grantee type in response")
            raise UnknownGranteeTypeError()

        if grantee_type == "user":
            grantee = UserItem.as_reference(grantee_id)
        elif grantee_type == "group":
            grantee = GroupItem.as_reference(grantee_id)
        else:
            raise UnknownGranteeTypeError("No support for grantee type of {}".format(grantee_type))

        return grantee
