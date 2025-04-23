class tamponDonnee:
    def __init__(self, max=100):
        self.taille_max = max
        self.donnees = []
    
    def ajouter(self, timestamp, temperature, moyenne):
        if len(self.donnees) >= self.taille_max:
            self.donnees.pop(0)  # Supprimer la plus ancienne entrée
        
        self.donnees.append({
            "timestamp": timestamp,
            "temperature": temperature,
            "moyenne": moyenne
        })

    def est_vide(self):
        return len(self.donnees) == 0

    def obtenir_prochain(self):
        if self.est_vide():
            return None
        return self.donnees[0]

    def supprimer_premier(self):
        if not self.est_vide():
            self.donnees.pop(0)