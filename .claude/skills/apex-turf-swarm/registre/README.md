# Registre WORM du swarm turf

`turf.jsonl` est **append-only et chaîné par hash**. Ne pas l'éditer à la main : toute
modification d'une ligne existante casse la chaîne et `worm.py verify` le signalera, en
nommant l'enregistrement en défaut.

Pour corriger un enregistrement, on **ajoute** une `correction` qui cite `corrige_seq` et
porte un `motif`. Les deux versions restent lisibles côte à côte. C'est le but.

```bash
python3 ../scripts/worm.py verify turf.jsonl
```
