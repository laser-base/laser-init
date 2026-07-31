- [ ] verify ISO-3 codes
- [ ] verify country list (and ISO mapping)
- [ ] verify French names (and ISO mapping)
- [ ] exact match results
- [ ] exact match testing
- [ ] local, fuzzy match results
- [ ] local, fuzzy match results testing
- [ ] OpenAI/ChatGPT results, public access (no API key)
- [ ] OpenAI/ChatGPT results, with API key
- [ ] Anthropic/Claude results, public access (no API key)
- [ ] Anthropic/Claude results, with API key
- [ ] UNOCHA/HDX shapefile extractor
- [ ] UNOCHA/HDX extractor tests
- [ ] GADM shapefile extractor
- [ ] GADM extractor tests
- [ ] geoBoundaries shapefile extractor
- [ ] geoBoundaries extractor tests
- [ ] WorldPop population extractor
- [ ] WorldPop population extractor tests
- [ ] ¿UN WPP population extractor?
- [ ] UN WPP population extractor tests
- [ ] population rasterization against shapefile
- [ ] Voronoi tesselation of shapes
- [ ] population rasterization against Voronoi tesselated shapes
- [ ] UN WPP age distribution extractor
- [ ] UN WPP bithrate data extractor
- [ ] UN WPP mortality data extractor
- [ ] .laser file with OpenAI or Anthropic API key

## Visualizations

1. Global incidence (stacked outcomes/compartments)
No change.

2. Global $R_t$
No change.

3. Choropleth snapshots of incidence per 100k (3–6 panels)
Replace the center×time heatmap with a small set of time slices (e.g., pre-wave, early growth, peak week, late decline, post-wave).

Use a fixed color scale across panels.

Consider log scale or winsorization if a few centers dominate.

4. Arrival-time choropleth (time-to-threshold)
Replace “arrival heatmap” with a map of first arrival: time to first case, or time to reach e.g. 1 per 100k/day (or cumulative 10 per 100k).

This is usually the single clearest visualization of spread.

5. Small multiples: incidence curves for top 12–20 centers
Still valuable. Maps show “where,” this shows “how big/how long” for representative places.

6. Imported vs local infections (global + 2–4 example centers)
No change, but now you can choose examples by geography: source-like hub, periphery, well-connected metro, rural region.

7. Peak timing vs peak size scatter
No change, but add geography-derived encoding:

color by region/state/province

or color by quantile of connectivity / centrality if you compute it from mobility.

8. Cumulative incidence per 100k distribution (violin/hist) + optional map of cumulative incidence
If you can afford 9 figures, add a final cumulative incidence choropleth.
If you must keep 8, do either:

distribution plot only (for inequality/heterogeneity), or

cumulative map only (for “where burden landed”), depending on audience.

## Mods

- stacked E and I
  - conside using top 12 or 16 nodes

- choropleth snapshots
  - consider using prevalence rather than absolute numbers

- import pressure should be choropleths, not line plots

- ranked cumulative incidence isn't conveying much
