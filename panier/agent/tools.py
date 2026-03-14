from langchain_core.tools import tool
from panier.models import Course, Panier


class AgentTools:
    """
    Factory d'outils LangGraph.
    Chaque appel à make_tools() crée un nouveau jeu d'outils
    avec l'utilisateur injecté par closure, sans mutation d'état.
    """

    def make_tools(self, user):
        """
        Retourne la liste des outils pour un utilisateur donné.
        `user` est capturé par closure dans chaque outil : pas de self.user
        pour éviter les effets de bord si make_tools est appelé plusieurs fois.
        """

        @tool
        def create_course(titre: str, ingredients: str) -> str:
            """
            Crée une nouvelle course (article de shopping) pour l'utilisateur.
            `titre` est le nom de la course, `ingredients` est la liste des
            articles séparés par des virgules ou des sauts de ligne.
            """
            course = Course.objects.create(
                titre=titre,
                ingredient=ingredients,
                created_by=user
            )
            return f"Course '{course.titre}' créée (id={course.id})"

        @tool
        def get_current_panier() -> str:
            """
            Retourne le panier le plus récent de l'utilisateur.
            Utilise le champ `user` (pas `created_by`) et `date_creation`.
            """
            # Logique famille : si le user a un nom de famille, on cherche
            # aussi les paniers des membres de la famille
            last_name = user.last_name
            if last_name:
                panier = Panier.objects.filter(
                    user__last_name__iexact=last_name
                ).order_by('-date_creation').first()
            else:
                panier = Panier.objects.filter(
                    user=user
                ).order_by('-date_creation').first()

            if not panier:
                return "Aucun panier trouvé. Tu peux en créer un avec l'outil create_panier."

            courses = list(panier.courses.values_list('titre', flat=True))
            courses_str = ', '.join(courses) if courses else 'aucune course'
            return (
                f"Panier #{panier.id} créé le {panier.date_creation.strftime('%d/%m/%Y')} "
                f"— courses : {courses_str}"
            )

        @tool
        def add_course_to_panier(course_id: int, panier_id: int = None) -> str:
            """
            Ajoute une course existante à un panier.
            Si panier_id n'est pas fourni, utilise le panier le plus récent.
            """
            try:
                course = Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                return f"Course id={course_id} introuvable."

            if panier_id:
                try:
                    panier = Panier.objects.get(id=panier_id)
                except Panier.DoesNotExist:
                    return f"Panier id={panier_id} introuvable."
            else:
                panier = Panier.objects.filter(user=user).order_by('-date_creation').first()
                if not panier:
                    return "Aucun panier disponible. Crée d'abord un panier."

            if course in panier.courses.all():
                return f"'{course.titre}' est déjà dans le panier #{panier.id}."

            panier.courses.add(course)
            return f"'{course.titre}' ajouté au panier #{panier.id}."

        @tool
        def create_panier() -> str:
            """
            Crée un nouveau panier vide pour l'utilisateur.
            """
            panier = Panier.objects.create(user=user)
            return f"Nouveau panier #{panier.id} créé."

        @tool
        def list_paniers() -> str:
            """
            Retourne la liste des paniers de l'utilisateur (et de sa famille).
            """
            last_name = user.last_name
            if last_name:
                paniers = Panier.objects.filter(
                    user__last_name__iexact=last_name
                ).order_by('-date_creation')[:5]
            else:
                paniers = Panier.objects.filter(
                    user=user
                ).order_by('-date_creation')[:5]

            if not paniers:
                return "Aucun panier trouvé."

            lignes = []
            for p in paniers:
                nb = p.courses.count()
                lignes.append(
                    f"Panier #{p.id} — {p.date_creation.strftime('%d/%m/%Y')} "
                    f"— {nb} course(s) — propriétaire: {p.user.username}"
                )
            return "\n".join(lignes)

        @tool
        def rag_search(query: str) -> str:
            """
            Répond aux questions sur l'interface de l'application PanierFacile :
            comment créer un panier, comment ajouter une course, etc.
            Utilise la base de connaissances UI.
            """
            from panier.utils import rag_system
            if not rag_system.qa:
                return "Le système d'aide n'est pas disponible pour l'instant."
            return rag_system.qa.invoke(query)

        return [
            create_course,
            get_current_panier,
            add_course_to_panier,
            create_panier,
            list_paniers,
            rag_search,
        ]
