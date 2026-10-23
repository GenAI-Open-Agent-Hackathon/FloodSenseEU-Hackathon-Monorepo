[out:json][timeout:180];
(
  nwr["building"~"^(industrial|warehouse|retail|commercial)$"]["name"](39.35,-0.63,39.50,-0.36);
  nwr["amenity"~"^(hospital|school|fire_station|police|clinic)$"](39.35,-0.63,39.50,-0.36);
  nwr["shop"~"^(supermarket|mall)$"](39.35,-0.63,39.50,-0.36);
  nwr["industrial"]["name"](39.35,-0.63,39.50,-0.36);
);
out center tags;
