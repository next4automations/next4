class MacroManager:
    def __init__(self):
        # Lista que guarda todas as ações da macro
        self.actions = []

    def add_action(self, action):
        """Adiciona uma ação à macro"""
        self.actions.append(action)

    def clear_actions(self):
        """Remove todas as ações"""
        self.actions.clear()

    def get_actions(self):
        """Retorna a lista de ações"""
        return self.actions
