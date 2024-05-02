#Importerer arcpy
import arcpy

#Definerer koordinatsystem
ETRS_1989_UTM_Zone_32N = arcpy.SpatialReference(25832)

#Definerer hvor resultatene skal lagres
resultat_gdb = r"C:\lagringsvei\GF_spredning.gdb"

arcpy.env.workspace = r"C:\lagringsvei\GF_spredning.gdb"

#Dersom koden kjøres flere ganger vil resultater overskrives
arcpy.env.overwriteOutput = True

#Manuelt: legg til vann og kommunes grenser i kartet

#Legge vann og kommunens grenser i geodatabasen
arcpy.conversion.FeatureClassToGeodatabase("Vann; Kommune", 
                                           resultat_gdb)

#Klippe vann til kommunes grenser
arcpy.Clip_analysis("Vann", 
                    "Kommune", 
                    "Vann_frstd")


#Definere studieområde for høydemodell

#slektere ut elv og hav fra studieområde for å senere klippe bort dette
arcpy.management.SelectLayerByAttribute("Vann_Frstd", 
                                        "NEW_SELECTION", 
                                        "objtype = 'Havflate' Or objtype = 'Elv' ", 
                                        None)

arcpy.conversion.ExportFeatures("Vann_Frstd", 
                                "HavElv_Frstd", 
                                "", "", "", "")

#Klippe bort hav og elv fra studieområdet
arcpy.analysis.Erase("Kommune", 
                     "HavElv_Frstd", 
                     "Frstd_uHavElv", 
                     None)

#Benytter denne dersom det dannes sliver polygoner
    #For å sette xy-toleranse måles sliver polygonene
with arcpy.EnvManager(XYTolerance="0.05 Meters"):
    arcpy.analysis.Erase("Kommune", 
                         "HavElv_Frstd", 
                         "Frstd_uHavElv", 
                         None)

#Manuelt: Legger til grunnforurensning i kartet

#Legge inn grunnforurensing i geodatabasen
arcpy.conversion.FeatureClassToGeodatabase("Grunnforurensning", 
                                           resultat_gdb)

#Klippe grunnforurensing til kommunens grenser
arcpy.analysis.Clip("Grunnforurensning", 
                    "Kommune", 
                    "GF_Frstd", 
                    None)

#Lage individuelle lag for de ulike påvirkningsgradene
paavirkningsgrader = {'GF3': 'ikkeAkseptabelForurensning', 'GF2':'akseptabelForurensning', 'GF1':'liteForurensning', 'GFX':'ukjentPåvirkning'}

for paav_kode, paav_navn in paavirkningsgrader.items(): 
    arcpy.management.SelectLayerByAttribute("GF_frstd", 
                                            "NEW_SELECTION", 
                                            f"påvirkningsgrad='{paav_navn}'", 
                                            None)
    
    arcpy.conversion.ExportFeatures("GF_frstd", 
                                    f"GF{paav_kode[-1]}", 
                                    "", "", "", "")

#Manuelt: legg til alle de sårbare områdene i kartet

#Importere sårbare lag til geodatabase
arcpy.conversion.FeatureClassToGeodatabase("SikraFriOm;Badepls;Beiteomr;DrikkOverflate;jordbruk;Kulturlandskp;NattypNiN;Naturtyp13;Bygg;Sti", resultat_gdb)

#Klippe alle lagene for sårbarhet til kommunens grenser

saarbarheter = ["Badepls", "Beiteomr", "Bygg", "DrikkOverflate", "jordbruk", "Kulturlandskp", "NattypNiN", "Naturtyp13", "SikraFriOm", "Sti"]
kommune = "Kommune"

for saarbarhet in saarbarheter:
    input_feature = f"{saarbarhet}"
    output_feature = f"{saarbarhet}_frstd"
    arcpy.Clip_analysis(
        input_feature, 
        kommune, 
        output_feature
    )

#Lage buffer rundt sårbare linje-temalag
arcpy.analysis.Buffer("Sti_frstd", 
                      "Sti5_frstd", 
                      "5 Meters", 
                      "FULL", 
                      "ROUND",
                      "", 
                      "", 
                      "PLANAR")

#Lage nye lag for hav og elv

#Lage et nytt polygontemalag for hav
arcpy.management.SelectLayerByAttribute("Vann_frstd", 
                                        "NEW_SELECTION", 
                                        "objtype = 'Havflate' ", 
                                        None)

arcpy.conversion.ExportFeatures("Vann_frstd", 
                                "Hav_frstd", 
                                "", "", "", "")

arcpy.SelectLayerByAttribute_management("Vann_frstd", 
                                        "CLEAR_SELECTION")

#Lage et nytt polygontemalag for elv
arcpy.management.SelectLayerByAttribute("Vann_frstd", 
                                        "NEW_SELECTION", 
                                        "objtype = 'Elv'", 
                                        None)

arcpy.conversion.ExportFeatures("Vann_frstd", "Elv_frstd", 
                                "", "", "", "")

arcpy.SelectLayerByAttribute_management("Vann_frstd", 
                                        "CLEAR_SELECTION")


#Manuelt: legge til alle tif-filene for høydedata i kartet

#Importere tif-filene til geodatabasen
input_rasters = "dtm1_33_125_110_tif;dtm1_33_125_109_tif;dtm1_33_125_108_tif;dtm1_33_124_110_tif;dtm1_33_124_109_tif;dtm1_33_124_108_tif;dtm1_33_123_110_tif;dtm1_33_123_109_tif;dtm1_33_123_108_tif"
arcpy.conversion.RasterToGeodatabase(input_rasters, 
                                     resultat_gdb, 
                                     "")

#Setter sammen de ulike tif-filene til en DHM
input_rasters = "dtm1_33_123_108_tif;dtm1_33_123_109_tif;dtm1_33_123_110_tif;dtm1_33_124_108_tif;dtm1_33_124_109_tif;dtm1_33_124_110_tif;dtm1_33_125_108_tif;dtm1_33_125_109_tif;dtm1_33_125_110_tif"

arcpy.management.MosaicToNewRaster(input_rasters,
                                    resultat_gdb,
                                    "DHM_UTM32",
                                    ETRS_1989_UTM_Zone_32N,
                                    "32_BIT_FLOAT",
                                    1,
                                    1,
                                    "MEAN", 
                                    "FIRST")

#Erstatte eventuelle null-verdier i DHM

#Definerer inngangsraster
input_raster = "DHM_UTM32"

#Definerer et nabolag av celler, og finner gjennomsnittsverdien i nabolagene
rFocstat = arcpy.sa.FocalStatistics(input_raster, 
                                    arcpy.sa.NbrRectangle(7,7,"CELL"), 
                                    "MEAN")

#Finner eventuelle null-verdier i inngangsrasteren
rIsNull = arcpy.sa.IsNull(input_raster)

#Eventuelle null verdier erstattes med gjennomsnittverdien for dette nabolaget
DHM_null = arcpy.sa.Con(rIsNull, 
                         rFocstat, 
                         input_raster)

#Lagrer resultatene fra de ulike verktøyene til geodatabasen
rFocstat.save("rFocstat")
rIsNull.save("rIsNull")
DHM_null.save("DHM_null")

#Klippe DHM til studieområdet
arcpy.management.Clip("DHM_null", 
                      "", 
                      "DHM_uHavElv", 
                      "Frstd_uHavElv", 
                      "", 
                      "ClippingGeometry", 
                      "NO_MAINTAIN_EXTENT")

#Definerer innstillinger for samtlige nye rasterlag
arcpy.env.cellSize = 1
arcpy.env.snapRaster = "DHM_uHavElv"
arcpy.env.extent = "DHM_uHavElv"

#Fyller forsenkninger i høydemodellen
rFill = arcpy.sa.Fill("DHM_uHavElv", 
                      "")

rFill.save('rFill')

#Inkluderer høyde på bygg i høydemodellen

#Rasteriserer byggninger i studieområdet
arcpy.conversion.PolygonToRaster("Bygg_frstd", 
                                 "OBJECTID", 
                                 "rBygg", 
                                 "MAXIMUM_AREA", 
                                 "", 
                                 1, 
                                 "BUILD")

#Reklassifisere bygningsrasteren
rBygg_Reklass = arcpy.sa.Reclassify(in_raster="rBygg",
                                    reclass_field="Value", 
                                    remap="1 74214 6;NODATA 0", 
                                    missing_values="DATA")
rBygg_Reklass.save("rBygg_Reklass")

#Slå sammen høydemodellen med de reklassifiserte bygningene
rBygg_Reklass = arcpy.Raster("rBygg_Reklass")
rFill = arcpy.Raster("rFill")

DHM_mBygg = arcpy.sa.Plus(in_raster_or_constant1=rBygg_Reklass, 
                          in_raster_or_constant2=rFill)
DHM_mBygg.save("DHM_mBygg")

#Inkluderer høyde for innsjøer i høydemodellen

#Lage et nytt polygontemalag for innsjø
arcpy.management.SelectLayerByAttribute("Vann_Frstd", 
                                        "NEW_SELECTION", 
                                        "objtype = 'Innsjø'", 
                                        None)

arcpy.conversion.ExportFeatures("Vann_Frstd", "Innsjo_Frstd", 
                                "", "", "", "")

#Rasterisere innsjø i studieområdet
arcpy.conversion.PolygonToRaster("Innsjo_Frstd", 
                                 "hoyde", 
                                 "rInnsjo", 
                                 "MAXIMUM_AREA", 
                                 "", 
                                 1, 
                                 "BUILD")

#Områder med innsjø blir tildelt verdien null
rInnsjo_isNull = arcpy.sa.IsNull("rInnsjo")
rInnsjo_isNull.save("rInnsjo_isNull")

#Slå sammen rasterlag for høydemodellen med bygg og innsjø
#Hvis null-verdier gis verdier fra innsjø, og hvis ikke tildeles verdier fra DHM med bygg
rInnsjoBygg = arcpy.sa.Con("rInnsjo_isNull", 
                           "DHM_mBygg", 
                           "rInnsjo", 
                           "")
rInnsjoBygg.save("rInnsjoBygg")

#Finner drenerningsrettninger
arcpy.gp.FlowDirection_sa("rInnsjoBygg", 
                          "rFlowDir", 
                          "NORMAL", 
                          "", 
                          "D8")

#Definerer påvirkningsgrader
paavirkningsgrader = ['GF3', 'GF2', 'GF1', 'GFX']
   
for paavirkningsgrad in paavirkningsgrader:
        
    #Fjerner grensene mellom polygoner som overlapper, innad i hver påvirkningsgrad
    arcpy.gapro.DissolveBoundaries(f"{paavirkningsgrad}", 
                                   f"GF{paavirkningsgrad[-1]}_akkml", 
                                   "SINGLE_PART", 
                                   None, None, None)
        
    #Kombinerer polygontemalaget for studieområdet og hver av de ulike påvirkningsgradene
    arcpy.analysis.Update("Kommune", 
                          f"{paavirkningsgrad}_akkml", 
                          f"Frstd_{paavirkningsgrad}", 
                          "BORDERS", 
                          "")

    #Legge til felt i atributt-tabellen til de ulike påvirkningsgradene, for å tildele verdier for nedbør
    arcpy.management.AddField(f"Frstd_{paavirkningsgrad}", 
                              "verdi", 
                              "LONG", 
                              "", "", "", "", 
                              "NULLABLE", 
                              "NON_REQUIRED", 
                              "")
    
    #Definerer atributt-tabeller og felter
    attributt_paavirkningsgrad = f"Frstd_{paavirkningsgrad}"
    felt = ['OBJECTID', 'verdi', 'Shape_Area']
        
    #Finne den maksimale Shape_Area-verdien
    max_shape_area = max(row[2] for row in arcpy.da.SearchCursor(attributt_paavirkningsgrad, felt))

    #Tildele verdier til nytt felt, verdien 100 gis til områder med grunnforurensning og verdien 0 hvis ikke
    with arcpy.da.UpdateCursor(attributt_paavirkningsgrad, felt) as cursor:
        for row in cursor:
            # Les verdier fra attributtabellen
            if row[2] == max_shape_area:
                row[1] = 0
            else:
                row[1] = 100
            cursor.updateRow(row)
            
    #lage rsterlag for hver av påvirkningsgradene
    arcpy.conversion.FeatureToRaster(f"Frstd_{paavirkningsgrad}", 
                                     "verdi", 
                                     f"r{paavirkningsgrad}", 
                                     1)

#Finne drenerningsakkumulasjonen med startpunkt gitt i de ulike påvirkningsgradene
for paavirkningsgrad in paavirkningsgrader:
    arcpy.gp.FlowAccumulation_sa("rFlowDir", 
                                 f"rFlowAcc_{paavirkningsgrad}", 
                                 f"r{paavirkningsgrad}", 
                                 "INTEGER", 
                                 "D8")

#Reklassifisere verdiene for drenerningslinjer
##kan ikke skrive som løkke for å få riktig navn i "contents"
rFlowAcc_GF3 = arcpy.Raster("rFlowAcc_GF3")
max_value = rFlowAcc_GF3.maximum
rFlowAcc5000_GF3 = arcpy.sa.Reclassify(rFlowAcc_GF3, "Value", f"0 5000 NODATA;5000 {max_value} 1", "DATA")
rFlowAcc5000_GF3.save("rFlowAcc5000_GF3")

rFlowAcc_GF2 = arcpy.Raster("rFlowAcc_GF2")
max_value = rFlowAcc_GF2.maximum
rFlowAcc5000_GF2 = arcpy.sa.Reclassify(rFlowAcc_GF2, "Value", f"0 5000 NODATA;5000 {max_value} 1", "DATA")
rFlowAcc5000_GF2.save("rFlowAcc5000_GF2")

rFlowAcc_GF1 = arcpy.Raster("rFlowAcc_GF1")
max_value = rFlowAcc_GF1.maximum
rFlowAcc5000_GF1 = arcpy.sa.Reclassify(rFlowAcc_GF1, "Value", f"0 5000 NODATA;5000 {max_value} 1", "DATA")
rFlowAcc5000_GF1.save("rFlowAcc5000_GF1")

rFlowAcc_GFX = arcpy.Raster("rFlowAcc_GFX")
max_value = rFlowAcc_GFX.maximum
rFlowAcc5000_GFX = arcpy.sa.Reclassify(rFlowAcc_GFX, "Value", f"0 5000 NODATA;5000 {max_value} 1", "DATA")
rFlowAcc5000_GFX.save("rFlowAcc5000_GFX")

#Gjør om drenerningslinjer fra rasterlag til linjelag
for paavirkningsgrad in paavirkningsgrader:
    arcpy.sa.StreamToFeature(in_stream_raster= f"rFlowAcc5000_{paavirkningsgrad}", 
                             in_flow_direction_raster= "rFlowDir", 
                             out_polyline_features= f"drenlinje_{paavirkningsgrad}", 
                             simplify ="SIMPLIFY")

paavirkningsgrader = ['GF3', 'GF2', 'GF1', 'GFX']

saarbare = ["Badepls", "Beiteomr", "Bygg", "DrikkOverflate", "Jordbruk", "Kulturlandskp",
            "NattypNiN", "Naturtyp13", "SikraFriOm", "Sti5", "Elv", "Hav"]

#lage lag for alle start noder til linjene
#finner deretter startnoder som overlapper med grunnforurensningene
for paavirkningsgrad in paavirkningsgrader:
    arcpy.management.FeatureVerticesToPoints(f"drenlinje_{paavirkningsgrad}", 
                                             f"FromNode_{paavirkningsgrad}_m", 
                                             "START")

    arcpy.analysis.Intersect(f"FromNode_{paavirkningsgrad}_m #;{paavirkningsgrad} #", 
                             f"FromNode_{paavirkningsgrad}", 
                             "ALL", 
                             None, 
                             "POINT")

from collections import deque 

def bfs_nedstrom(start_punkt_from_node, start_punkt_to_node, dreneringslinjer):
    """
    Gjør et bredde-først-søk (BFS) nedstrøms fra et gitt startpunkt.

    Parametere:
    start_punkt_from_node (int): "from_node" til start linja.
    start_punkt_to_node (int): "to_node" til start linja.
    dreneringslinjer (str): Linjelaget vi vil bruke for å finne nedstrømslinjer.

    Returns:
    arcpy.Polyline: En linje fra startpunkt til endepunkt nedstrøms.
    """
    #En dict for å lagre linje shape og to_node med from_node som nøkkel
    linje_dict = {}

    #Går gjennom alle linjene og lager nøkkel - verdi par
    with arcpy.da.SearchCursor(dreneringslinjer, ["from_node", "to_node", "Shape@"]) as cursor:
        for row in cursor:
            #Leser ut verdier fra attributtabellen
            from_node = row[0]
            to_node = row[1]
            shape = row[2]
            # Legg til i linje_dict
            linje_dict[from_node] = [shape, to_node]

    #Lager en kø og legger til to_node til start linja
    linje_ko = deque([start_punkt_to_node])

    #Legger til start linja i leste over nedstrømslinjer
    start_linje = linje_dict[start_punkt_from_node][0]
    resultat_linjer = [start_linje]

    #Traverserer linjelaget og finner alle tilknyttede nedstrømslinjer med bfs
    while linje_ko:
        #Henter den noden som er først i køen, dette er en from_node
        soke_node = linje_ko.popleft()
        
        #Sjekker om linja fortsetter
        if soke_node in linje_dict:
            #Henter ut nedstrømslinjen fra linje_dict og legger den til i resultat_linjer
            linje = linje_dict[soke_node][0]
            resultat_linjer.append(linje)
            
            #Henter ut to_noden til linja vi jobber med
            to_node = linje_dict[soke_node][1]
            
            #Sjekker om enden på linja er koblet til nye nedstrømslinjer
            if to_node in linje_dict:
                #Legger til to_noden i køen for videre søk
                linje_ko.append(to_node)
                
    #BFS er ferdig og hele nedstrømslinja fra start_punkt_from_node er funnet
    #Slår sammen alle dellinjene
    sammenslaatt_linje_array = arcpy.Array()
    for linje in resultat_linjer:
        sammenslaatt_linje_array.extend(linje)

    #Endre datatype til Polyline
    sammenslaatt_linje = arcpy.Polyline(sammenslaatt_linje_array)

    #Så returnerer vi den sammenslåtte linja
    return sammenslaatt_linje


for paavirkningsgrad in paavirkningsgrader:
    #Definer output laget
    resultat_lag = f"Nedstrom_{paavirkningsgrad}"
    
    #Lag feature class for output laget og legg til felt for FID_grunnforurensning
    arcpy.management.CreateFeatureclass(resultat_gdb, 
                                        resultat_lag, 
                                        "POLYLINE", 
                                        None, 
                                        "DISABLED", 
                                        "DISABLED", 
                                        ETRS_1989_UTM_Zone_32N, 
                                        "", 0, 0, 0, "")
    
    arcpy.management.AddField(resultat_lag, 
                              f"FID_{paavirkningsgrad}", 
                              "SHORT")
    
    #Lag en cursor for å legge til verdier i output laget
    insert_cursor = arcpy.da.InsertCursor(resultat_lag, 
                                          ["Shape@", f"FID_{paavirkningsgrad}"]) 
    
    #Linjelaget vi skal undersøke
    dreneringslinjer = f"drenlinje_{paavirkningsgrad}"
    
    #Laget med alle start punktene for nedstrømslinjene vi vil ha
    from_node_lag = f"FromNode_{paavirkningsgrad}"
    
    #Gå gjennom alle start punktene 
    with arcpy.da.SearchCursor(from_node_lag, 
                               ["to_node", "from_node", 
                                f"FID_{paavirkningsgrad}", 
                                "OID@"]) as cursor:
        for row in cursor:
            #Les verdier fra attributtabellen
            to_node = row[0]
            from_node = row[1]
            fid_paavirkningsgrad = row[2]
            
            #Finn nedstrømslinje fra startpunkt med BFS algoritme
            sammenslaatt_linje = bfs_nedstrom(from_node, to_node, dreneringslinjer)
            
            #Legg til den sammenslåtte linja med tilhørende fid_GF i output laget
            insert_cursor.insertRow((sammenslaatt_linje, fid_paavirkningsgrad))
            
    #Slett insert cursoren for å unngå feilinnsettinger
    del insert_cursor

#Slår sammen linjene basert på gf, slik at hver gf har en rad i attributt-tabellen

for paavirkningsgrad in paavirkningsgrader:
    arcpy.management.Dissolve(f"Nedstrom_{paavirkningsgrad}", 
                             f"saarbar_{paavirkningsgrad}_m", 
                              f"FID_{paavirkningsgrad}", 
                              None, 
                              "MULTI_PART", 
                              "DISSOLVE_LINES", 
                              "")

#Legger til et felt i atributt-tabellen til de ulike lagene med drenenringslinjer koblet til GF-områder

#Legg til felt for hvert av de sårbare områdene i tabellen til dreneringslinjene
for paavirkningsgrad in paavirkningsgrader:
    arcpy.management.AddField(f"saarbar_{paavirkningsgrad}_m", 
                              "Sum", 
                              "SHORT")
    
    #Legger til "sum" for å summere opp overlappende områder mellom sårbare områder og GF
    for saarbar in saarbare:
        arcpy.management.AddField(f"saarbar_{paavirkningsgrad}_m", 
                                  saarbar, 
                                  "SHORT")

#Tillegge dreneringslinjer buffer 
for paavirkningsgrad in paavirkningsgrader:
    arcpy.analysis.Buffer(f"saarbar_{paavirkningsgrad}_m", fr"saarbar_{paavirkningsgrad}", "5 Meters", "FULL", "ROUND", "NONE", None, "PLANAR")

#Finne hvilke grunnforurensingslokaliteter som overlapper med sårbare områder

for paavirkningsgrad in paavirkningsgrader:
    for saarbar in saarbare:
        print(f"Jobber med {paavirkningsgrad} og {saarbar}")
        with arcpy.da.UpdateCursor(f"saarbar_{paavirkningsgrad}", ["SHAPE@", saarbar, "Sum"]) as cursor:
            for row in cursor:
                dreneringslinje = row[0]
                
                #Finner sårbare områder og grunnforurensningslokaliteter som overlapper
                arcpy.management.SelectLayerByLocation(f"{saarbar}_frstd", "INTERSECT", dreneringslinje)
                antall_intersections = int(arcpy.management.GetCount(f"{saarbar}_frstd")[0])
                
                 #Dersom overlapp 1, hvis ikke 0
                    #summerer opp antall overlapp per grunforurensningslokalitet
                if row[2] is None:
                    row[2] = 0 
                if antall_intersections > 0:
                    row[1] = 1
                    row[2] += 1
                else:
                    row[1] = 0
                
                #De selekterte sårbare områdene klareres, for å ikke påvirke neste søk
                cursor.updateRow(row)
                arcpy.management.SelectLayerByAttribute(f"{saarbar}_frstd", "CLEAR_SELECTION")

#Slå sammen polygonene for grunnforurensning og drenerningslinjene 
#Dette for å symbolisere den totale summen av påvirkning for GF-lokalitetene

felter = [*saarbare, "Sum"]

for paavirkningsgrad in paavirkningsgrader:
    arcpy.management.JoinField(f"{paavirkningsgrad}", 
                               "OBJECTID", 
                               f"saarbar_{paavirkningsgrad}", 
                               f"FID_{paavirkningsgrad}", 
                               felter)

#Finne hvilke sårbare områder som overlapper med drenerningslinjene fra grunnforurensningslokasjoner
#Lager nye lag for hvert av de ulike sårbare områdene som overlapper
#For å visualisere hvor de sårbare områdene er lokalisert
for paavirkningsgrad in paavirkningsgrader:
    for saarbar in saarbare:
        Resultat = arcpy.management.SelectLayerByLocation(fr"{saarbar}_frstd", "INTERSECT", f"saarbar_{paavirkningsgrad}", None, "NEW_SELECTION", "NOT_INVERT")
        arcpy.conversion.ExportFeatures(fr"{saarbar}_frstd", f"GF{paavirkningsgrad[-1]}_{saarbar}", "", "NOT_USE_ALIAS", "", None)
        arcpy.management.SelectLayerByAttribute(f"{paavirkningsgrad}_{saarbar}", "CLEAR_SELECTION")
