# Poolette — Cahier des charges (v1)

*« Est-ce que la piscine est ouverte ? Demande à Poolette ! »*
Rédigé le 10/11/2026 — à valider par Anne-Claire avant développement.

---

## 1. Objectif
Application mobile (PWA) qui indique, en un coup d'œil, **quelles piscines municipales sont ouvertes au public**, et jusqu'à quelle heure, autour de la position réelle de l'utilisatrice, pour un moment choisi (maintenant, aujourd'hui, demain, autre date, avec plage horaire).

## 2. Utilisateurs
- Usage **personnel** d'abord (Anne-Claire, iPhone). Partage possible ensuite, y compris Android.
- Usage : **nage sportive** (lignes d'eau). Les informations affichées ne concernent que le bassin de nage, jamais les petits bassins ou bassins ludiques.

## 3. Périmètre
- Piscines **municipales** jusqu'à **20 km** de chez elle (Toulouse et banlieue large). Les piscines privées et centres type Calicéo sont exclus.
- Rayon de recherche réglable dans l'appli : **10 km par défaut**, de 1 à 20 km.
- Français uniquement.

## 4. Critère « ouvert »
- Base : **ouvert au public**. Les créneaux de nage par ligne d'eau n'étant publiés presque nulle part, ils ne peuvent pas être le critère.
- Quand la source le permet (cas de L'Union : créneaux adultes), un repère « créneau adultes » s'ajoute.
- **Règle sur les bassins** : l'information ne compte que si elle concerne le **bassin de nage** de la piscine.
  - Fermeture ou réservation d'un petit bassin : **ignorée**, rien n'est affiché.
  - Bassin de nage fermé ou fortement réduit (ex. Toulouse Lautrec : bassin intérieur en travaux, seul le bassin nordique est ouvert) : **avertissement affiché**.
  - Chaque piscine a donc, dans la configuration, une fiche « bassin de nage » (nom, longueur, particularités).

## 5. Fonctionnalités

### 5.1 Écran principal
- Sélecteur de moment en 2 taps : *Maintenant · Aujourd'hui · Demain · Autre date* + plage horaire (ex. 12h–14h).
- Liste triée par distance (km routiers), chaque ligne : **nom (commune), distance, pastille de statut, heures d'ouverture et de fermeture**.
- Vue carte en alternative (bouton de bascule).
- **Favoris** épinglés en haut de la liste.
- Mention de fraîcheur : « Vérifié aujourd'hui à 6h ».

### 5.2 Statuts (pour le moment et la plage choisis)
| Statut | Couleur | Condition |
|---|---|---|
| Ouvert | Vert | Ouvert pendant toute la plage, avec au moins 60 min restantes |
| Ferme bientôt | Orange | Reste moins de 60 min (seuil réglable) |
| Fermé | Rouge/gris | Fermé sur la plage |
| Non vérifié | Gris hachuré | Données de plus de 48 h, extraction en échec ou doute |

- L'appli affiche uniquement l'heure de fermeture officielle. La pastille orange (moins de 60 min) suffit à signaler une fermeture proche : aucun détail sur l'évacuation du bassin ni sur la fermeture de la caisse.
- Les fermetures exceptionnelles (compétitions, travaux, jours fériés, canicule) prévalent sur les horaires réguliers.

### 5.3 Fiche piscine
Nom, adresse, distance, horaires du jour et de la semaine, avertissements éventuels sur le bassin de nage, bouton **Itinéraire** (ouvre Plans/Google Maps), bouton favori.

### 5.4 Réglages
Rayon, seuil orange, piscines masquées, thème clair/sombre.

## 6. Données
### 6.1 Liste des piscines
- Source : open data Toulouse Métropole (adresses et coordonnées, Licence Ouverte) + OpenStreetMap pour les communes hors Toulouse.
- Chaque piscine est identifiée en interne par un **identifiant stable et ses coordonnées**, pas par son nom (deux « Alex Jany » existent : Toulouse et Ramonville).
- **Affichage : toujours nom + commune**, partout dans l'appli (liste, carte, fiche, favoris), par exemple *Alex Jany (Toulouse)* et *Alex Jany (Ramonville-Saint-Agne)*.

### 6.2 Horaires : extraction automatique
- **GitHub Actions** : passage quotidien à 6h, éventuellement un second à 12h.
- Pour chaque piscine, téléchargement de la page officielle (ou du PDF/de l'image) et comparaison avec la veille (empreinte).
- **Si la page a changé** : envoi à l'API Claude, qui renvoie un JSON structuré (périodes, créneaux, exceptions datées). Validation automatique du format.
- **Si rien n'a changé** : on conserve les données, sans coût.
- Les zones « En bref » / bandeaux d'alerte sont traitées en priorité.
- Résultat enregistré dans le dépôt (`horaires.json`), lu par la PWA.
- Échec ou page inaccessible : alerte envoyée et piscine passée en « non vérifié » après 48 h.

### 6.3 Calendrier
- Vacances scolaires **zone C** (Toulouse) : jeu de données officiel de l'Éducation nationale.
- Jours fériés : calendrier officiel de l'État.

## 7. Distance
- Distance **routière en km** via une API de routage (OpenRouteService, offre gratuite), calculée pour les piscines dans le rayon.
- Repli sur la distance à vol d'oiseau, signalée par « ~ ».
- Pas de durée de trajet (dépend du trafic).
- Position : géolocalisation du navigateur (HTTPS, autorisation demandée une fois).

## 8. Technique
- **PWA** hébergée sur **GitHub Pages**, installable sur l'écran d'accueil iPhone (Safari) et Android (Chrome).
- Fonctionnement hors-ligne partiel : dernières données connues avec leur date.
- Code simple et léger (HTML/CSS/JS), avec les données séparées de l'interface pour permettre l'extension à d'autres villes.
- Clé du service de routage : restreinte au domaine du site. Si l'appli est largement partagée, un petit relais serveur sera nécessaire.

## 9. Design
- Sobre, professionnel, très ergonomique : utilisable d'une main, statut lisible en 1 seconde (grande pastille verte/orange/rouge), gros éléments tactiles.
- Mode sombre, icône et écran de lancement soignés, identité « Poolette » (nom, logo, palette à définir).
- Accessibilité : contraste suffisant, couleur toujours doublée d'un texte (« Ouvert », « Ferme bientôt »).

## 10. Coûts
| Poste | Coût |
|---|---|
| Hébergement GitHub Pages et Actions | 0 € |
| API Claude (extraction, uniquement quand une page change) | ~1 à 3 €/mois |
| Routage OpenRouteService (offre gratuite) | 0 € |

## 11. Limites assumées
1. Les créneaux de nage par ligne d'eau ne sont presque jamais publiés : le statut vert signifie « ouvert au public », pas « lignes d'eau garanties ».
2. Les pannes imprévues, annoncées seulement sur place ou sur les réseaux sociaux, ne sont pas détectables. Piste ultérieure : bouton « Signaler une fermeture ».
3. Aucune page ne donne de date de mise à jour : la fraîcheur repose sur le contrôle quotidien de Poolette.
4. Une extraction par IA peut se tromper : les cas douteux passent en « non vérifié » plutôt que d'afficher une information incertaine.

## 12. Plan de livraison
| Phase | Contenu |
|---|---|
| 0. Audit complémentaire | **Fait le 10/11/2026** (résultats en section 14). Reste : relancer Blagnac et Saint-Orens depuis GitHub Actions, trouver la source de Balma |
| 1. MVP | Toulouse + L'Union, statuts, distance, favoris, extraction quotidienne |
| 2. Couverture complète | Toutes les piscines à moins de 20 km, carte, fiches détaillées |
| 3. Ouverture | Partage à d'autres utilisateurs, signalements, autres villes |

## 13. Points à valider
- [ ] Clé API Claude à créer (via ton compte Anthropic) : OK de principe donné, création à faire.
- [ ] Validation de la liste des piscines à moins de 20 km (je la propose après l'audit complémentaire).
- [ ] Identité visuelle : une préférence de couleur ou de style pour Poolette ?
- [ ] Faut-il une notification (ex. « Ta piscine favorite ouvre à 12h ») ? Option hors périmètre pour l'instant.

---

## 14. Résultats de l'audit de faisabilité (10/11/2026)

| Piscine | Source | Format | Verdict |
|---|---|---|---|
| **Toulouse** (≈11 piscines, dont Alex Jany et Toulouse Lautrec) | Une page officielle par piscine sur metropole.toulouse.fr + un PDF global | Texte HTML par période, bandeaux « En bref » pour les exceptions | **Très bon.** Un seul modèle d'extraction pour toutes. |
| **L'Union** | ville-lunion.fr | Texte (créneaux) ; les 4 images sont de simples affiches de cours de la Toussaint | **Bon.** Le texte reste la source ; il faut lire la structure HTML pour savoir quelle catégorie correspond à quel créneau. |
| **Ramonville (Alex Jany)** | ramonville.fr | Liste HTML, bassin de 25 m à 4 couloirs | **Partiel.** Horaires de période scolaire seulement : rien pour les vacances ni l'été. |
| **Colomiers (Espace nautique Jean-Vauchère)** | ville-colomiers.fr | Tableau HTML, bassin sportif de 6 lignes de 25 m | **Source périmée.** Horaires valables « sept. 2025 à août 2026 », mis à jour le 24/02/2026. |
| **Balma** | mairie-balma.fr | Aucun horaire sur le site officiel | **Source à trouver** (probablement Facebook ou un autre site). |
| **Blagnac, Saint-Orens** | — | Non lus (site injoignable / adresse introuvable depuis l'outil d'audit) | **Non audité.** À retenter depuis GitHub Actions. |

### Ce que l'audit change dans la conception
1. **Le PDF de Toulouse est cohérent avec les pages** (vérifié sur Alex Jany et Lautrec, millésime 2026-2027), mais l'extraction du texte perd l'alignement des colonnes dans les cellules à plusieurs créneaux. Les **pages HTML** sont donc la source principale, le PDF sert de recoupement.
2. **Il faut détecter la validité d'une source** : l'extraction doit relever la période de validité du tableau et passer la piscine en « non vérifié » si elle est échue (cas de Colomiers).
3. **Une période sans horaires publiés** (Ramonville en vacances) s'affiche en « non vérifié », jamais déduite des autres périodes.
4. **Des sites commerciaux non officiels portent des noms trompeurs** (balma.fr, colomiers.fr). Les URL officielles de chaque piscine sont donc saisies à la main dans la configuration, pas découvertes automatiquement.
5. **Les fermetures exceptionnelles sont bien publiées** (Alex Jany fermée les 21 et 22 novembre, Ramonville fermée le 5 novembre pour grève, 11 novembre variable selon les piscines) : le contrôle quotidien est utile.
6. **La fiche « bassin de nage » est réalisable** : les pages décrivent les bassins (nombre de lignes, longueur), mais jamais les créneaux par ligne d'eau.

---

## 15. État du MVP (10/11/2026)

- **Livré** : application PWA (liste, carte, favoris, plage horaire, rayon, seuil orange, mode sombre), lecture automatique de **11 piscines de Toulouse** (sans IA), calendrier zone C et jours fériés, fermetures exceptionnelles, 26 tests de logique, workflow GitHub Actions quotidien.
- **Piscines de Toulouse couvertes** : Alban Minville, Alex Jany, Bellevue, Castex, Chapou (saisonnière), Jean Boiteux, Léo Lagrange, Nakache, Papus, Toulouse Lautrec, Yvonne Godard.
- **L'Union** : présente dans la liste mais « non vérifiée » tant que la clé API Claude n'est pas configurée (et son site affichait une erreur de base de données lors du test).
- **Non testé** : l'extraction par l'API Claude (pas de clé à ce stade) et le workflow GitHub (pas de dépôt encore).
- **Phase 2** : Ramonville, Colomiers, Balma (via Google Places), Blagnac, Saint-Orens ; distance routière (clé OpenRouteService) ; relais pour la clé si l'appli est ouverte à d'autres.
