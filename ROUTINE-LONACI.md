# Recréer la Routine APEX-TURF-WORM avec ses connecteurs

> Pourquoi par l'interface : le paramètre `connectors` de `create_trigger` est **refusé au
> niveau de l'organisation** (« the connectors parameter is not available for this
> organization »), et `update_trigger` n'en a pas. Seule l'interface Routines de claude.ai
> peut attacher des connecteurs à une Routine.

## Où

**claude.ai → Routines → Nouvelle routine.**

## Champs

| Champ | Valeur |
|---|---|
| Nom | `APEX-TURF-WORM horaire (périmètre LONACI)` |
| Planification | **toutes les heures, de 08h00 à 19h00 UTC** (cron `0 8-19 * * *`) |
| Fuseau | UTC — identique à Abidjan, donc l'heure affichée est l'heure locale |
| Session | **nouvelle session à chaque exécution** |
| Dépôt | `okomaleonce-commits/Apex-TSS`, branche `claude/apex-turf-worm-mi` |
| Notifications | push |

## Connecteurs à cocher — les deux sont nécessaires

| Connecteur | Sert à | Sans lui |
|---|---|---|
| **Firecrawl** (ou tout outil rendant le JavaScript) | lire le programme LONACI | la Routine s'arrête à l'étape 0, aucun périmètre |
| **Gmail** (`okoma.leonce@gmail.com`) | envoyer le digest | digest construit, non envoyé |

Firecrawl est le plus important des deux : sans lui, rien ne démarre. Gmail peut être
remplacé par les variables `WORM_SMTP_*` dans l'environnement (voir plus bas).

## Prompt à coller

```
Passage horaire APEX-TURF-WORM, restreint au programme officiel PMU LONACI.

Dépôt okomaleonce-commits/Apex-TSS, branche `claude/apex-turf-worm-mi`. Attache-le et
clone-le si besoin. `export APEX_TIMEZONE=Africa/Abidjan` (la Côte d'Ivoire est à UTC+0).

## 0. Vérification préalable — ÉCHOUE VITE ET EN UNE LIGNE

Cette Routine a besoin d'un moteur de rendu pour lire le programme LONACI. Vérifie
d'abord si tu en as un (`mcp__Firecrawl__firecrawl_scrape`, chargé via ToolSearch).

**Si aucun moteur de rendu n'est disponible : ARRÊTE IMMÉDIATEMENT** et réponds exactement
une ligne, sans rien tenter d'autre, sans rapport long, sans analyse de repli :

`BLOQUÉ — aucun moteur de rendu : le périmètre LONACI ne peut pas être lu.`

C'est une sortie valide et attendue. Ne scanne PAS le programme français entier à la
place : ce serait ignorer la demande. N'invente aucun périmètre. Ne réessaie pas.

## 1. Périmètre LONACI du jour

- Récupère le texte rendu de `https://pmu.lonacionline.ci/mobile/` (page publique, sans
  login, application Angular : `curl` et `WebFetch` ne rendent rien — vérifié).
  Firecrawl scrape, `maxAge: 0`, `waitFor: 8000`.
- Écris-le dans un fichier, un champ par ligne dans l'ordre de la page : code `R#C#`,
  hippodrome, libellé, heure, puis l'état (« Fin de course », ou la ligne discipline du
  type « Attelé-2150m-15 Partants »).
- `python3 tools/apex_turf_lonaci.py scope --date <DDMMYYYY> --from-text <fichier>`

Aucun code `R#C#` dans la page → même arrêt en une ligne qu'au point 0.
Nom de course discordant → le dire : le périmètre est peut-être périmé.

## 2. Scanner

python3 tools/apex_turf_worm.py scan --lonaci
python3 tools/apex_turf_mi.py worm-hook --within 30

Le premier passage du jour ne produit aucun signal (`PREMIER_PASSAGE`) : sans deuxième
relevé il n'y a pas de trajectoire. C'est correct, pas un échec.

## 3. Digest — deux voies, dans cet ordre

Règle du `CLAUDE.md` du dépôt : **un passage sans email envoyé est INCOMPLET.**

a) SMTP, automatique. Si l'environnement porte `WORM_SMTP_HOST`, `WORM_SMTP_USER`,
`WORM_SMTP_PASS` et `WORM_EMAIL_TO`, le scan a déjà envoyé seul et affiché
« EMAIL ENVOYE par SMTP ». Rien à faire : reprends cette ligne dans ton rapport.

b) Connecteur Gmail. Sinon, le scan a écrit `reports/turf_worm/<jour>.email.html` et
`.email.subject.txt` sans rien envoyer. Envoie-le avec `mcp__Gmail__send_message`
(`to = ["okoma.leonce@gmail.com"]`, `subject` et `htmlBody` depuis ces fichiers). La
preuve est l'`id` / `threadId` Gmail.

Si ni l'un ni l'autre n'est disponible, dis-le franchement : « digest construit, NON
ENVOYÉ, ni SMTP ni connecteur Gmail ». Ne laisse jamais croire qu'il est parti.

## Interdits

- Jamais de signal de pari. Palier maximal SURVEILLER, `autorite_pari=false`,
  `unites=0`. Les deux gates turf sont fermées par le backtest (trot ROI −4,58 % sur
  118 paris, obstacle −89,05 % sur 21).
- Jamais de plat ni de course marocaine : `HORS_PERIMETRE`, `ABSENT_SOURCE`. Les
  coefficients ne se transposent pas d'une discipline à l'autre.
- Jamais présenter les cotes comme celles de LONACI : elles viennent du PMU français
  (`cotes_origine: PMU_FRANCE`), et la masse d'enjeux LONACI n'est pas vérifiée.
  L'avertissement est dans le rapport — ne l'efface pas.
- Jamais inventer un chiffre, une cote ou un résultat. Donnée absente = écrite absente.
- Ne commite rien, ne pousse rien. Snapshots et rapports sont ignorés par `.gitignore`.

## Rapport final — trois lignes maximum

Courses au programme LONACI et combien dans le périmètre des moteurs · nombre de signaux
SURVEILLER · voie d'envoi et sa preuve. « Aucun signal au-dessus de 45/100 » est une
sortie valide.
```

## Après

Ma Routine `trig_01LAzCEBZRhuPaZQXtuai68Y` deviendra un doublon : dites-le-moi et je la
supprime. En attendant elle reste active et répondra `BLOQUÉ` en une ligne à chaque
passage, sans rien inventer.

## Option sans Gmail

Pour que l'envoi se fasse sans aucun connecteur, renseigner dans les variables
d'environnement :

```
WORM_SMTP_HOST   serveur SMTP
WORM_SMTP_USER   identifiant
WORM_SMTP_PASS   mot de passe d'application
WORM_EMAIL_TO    okoma.leonce@gmail.com
WORM_SMTP_PORT   587 par défaut (465 pour du SSL direct)
WORM_EMAIL_FROM  par défaut WORM_SMTP_USER
```

`apex_turf_worm.py` envoie alors seul, en STARTTLS. **Firecrawl reste nécessaire** :
le SMTP ne règle que l'étape 3.
