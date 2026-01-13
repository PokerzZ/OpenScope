import yaml
import networkx as nx
import os
from inference.base.graph import Graph
from pyvis.network import Network
from agent.agent_info.actions import REASONING_ACTION_LIST, TOOL_ACTION_LIST, TERMINATION_ACTION_LIST

class ActionGraph(Graph):
    def __init__(self):
        super().__init__()
        self.REASONING_ACTION_LIST = REASONING_ACTION_LIST
        self.TOOL_ACTION_LIST = TOOL_ACTION_LIST
        self.TERMINATION_ACTION_LIST = TERMINATION_ACTION_LIST
        
        # Get the absolute path to the config file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # ChatDev/puppeteer/inference/graph/action_graph.py -> ChatDev/puppeteer/
        project_root = os.path.abspath(os.path.join(current_dir, "../.."))
        config_path = os.path.join(project_root, "config/global.yaml")

        if os.path.exists(config_path):
            global_config = yaml.safe_load(open(config_path, "r"))
        else:
            global_config = yaml.safe_load(open("./config/global.yaml", "r"))
            
        external_tools_enabled = global_config.get("external_tools_enabled")
        if external_tools_enabled:
            self.actions_collection = REASONING_ACTION_LIST + TOOL_ACTION_LIST + TERMINATION_ACTION_LIST
        else:
            self.actions_collection = REASONING_ACTION_LIST + TERMINATION_ACTION_LIST


    def add_action(self, action_id, action_data, agent_data):
        self._add_node({"id": action_id, "action": action_data, "agent": agent_data})

    def add_dependency(self, from_action_id, to_action_id):
        self._add_edge(from_action_id, to_action_id, len(self._edges))

    def visualize(self, path="action_graph.html"):
        G = nx.DiGraph()
        nodes_colors = []
        for node in self._nodes:
            G.add_node(node["id"], label=node["action"]["action"]["action"] + "\n" + node["agent"], 
                       status=node["action"]["success"], 
                       color="green" if node["action"]["success"] == "Success" else "red")
            nodes_colors.append("green" if node["action"]["success"] == "Success" else "red")
        for edge in self._edges:
            G.add_edge(edge.u, edge.v)
        net = Network(notebook=False, height="750px", width="100%", bgcolor="#FFFFFF", font_color="black", directed=True)
        net.from_nx(G)
        net.save_graph(path)

    def get_action_data(self, action_id):
        for node in self._nodes:
            if node["id"] == action_id:
                return node
        return None
    
    def get_dependencies(self, action_id):
        return [edge.v for edge in self._edges if edge.u == action_id]