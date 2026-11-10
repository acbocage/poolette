# Poolette

*Est-ce que la piscine est ouverte ? Demande à Poolette !*

Application web mobile (PWA) qui indique quelles piscines municipales sont **ouvertes au public** autour de toi, jusqu'à quelle heure, pour maintenant, aujourd'hui, demain ou une date choisie (avec plage horaire). Cahier des charges : [cahier-des-charges.md](cahier-des-charges.md).

## Contenu du dossier

| Chemin | Rôle |
|---|---|
| `site/` | L'application publiée (HTML/CSS/JS, sans dépendance à installer) |
| `site/pools.json` | La liste des piscines : nom, commune, coordonnées, URL officielle, bassin de nage, avertissements |
| `site/data/` | Données générées chaque jour : `horaires.json`, `calendar.json`. `exceptions.json` : fermetures exceptionnelles |
| `scripts/update_data.py` | Lit les pages officielles, met à jour les données (Python, sans dépendance) |
| `scripts/make_icons.py` | Régénère les icônes PNG |
| `tests/logic.test.html` | Tests de la logique des statuts (ouvrir dans le navigateur) |
| `.github/workflows/update.yml` | Mise à jour automatique quotidienne + déploiement GitHub Pages |

## Essayer en local

```bash
python -m http.server 8765
```

Puis ouvrir `http://localhost:8765/site/` (l'appli) ou `http://localhost:8765/tests/logic.test.html` (les tests : le titre de l'onglet affiche `OK 26/26`).

## Mettre en ligne (GitHub Pages)

1. Créer un dépôt GitHub et y envoyer le contenu de ce dossier.
2. **Settings → Pages → Source : GitHub Actions.**
3. *(Recommandé)* **Settings → Secrets and variables → Actions → New repository secret** : `ANTHROPIC_API_KEY` (clé API Claude). Sans elle, Toulouse fonctionne quand même ; L'Union reste « non vérifié » et les exceptions du bandeau « En bref » restent celles saisies à la main dans `site/data/exceptions.json`.
4. **Actions → Poolette → Run workflow** pour le premier déploiement. L'adresse du site s'affiche dans le résultat.
5. Sur iPhone : ouvrir le site dans Safari → Partager → **Sur l'écran d'accueil**. Sur Android : menu Chrome → **Installer l'application**.

## Distance routière réelle (facultatif)

Sans réglage, Poolette affiche la distance **à vol d'oiseau** précédée de « ~ ». Pour la distance routière : créer une clé gratuite sur openrouteservice.org, la restreindre à l'adresse de ton site, puis la coller dans `orsKey` de `site/js/config.js`.

## Ajouter une piscine

Ajouter une entrée dans `site/pools.json` (URL **officielle** de la mairie : des sites commerciaux homonymes existent). Les pages `metropole.toulouse.fr/annuaire/piscine-…` sont lues sans IA ; toute autre page (`"type": "llm_page"`) demande la clé `ANTHROPIC_API_KEY`.

## Ce que Poolette ne sait pas

- Les créneaux par ligne d'eau ne sont publiés nulle part : « ouvert » signifie ouvert au public.
- Les pannes imprévues non publiées sur le site officiel ne sont pas détectables.
- Une source périmée ou une période sans horaires publiés passe en **« Horaires non vérifiés »** (gris), jamais en estimation.
