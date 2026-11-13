// Réglages de Poolette.
// orsKey : clé OpenRouteService (gratuite, https://openrouteservice.org) pour la distance ROUTIÈRE réelle.
// Sans clé, Poolette affiche la distance à vol d'oiseau, précédée de « ~ ».
// Restreins la clé au domaine de ton site dans le tableau de bord OpenRouteService.
export const CONFIG = {
  orsKey: '',
  defaultCenter: { lat: 43.6045, lon: 1.4442, label: 'Toulouse centre' },
  maxRadiusKm: 60,
};
