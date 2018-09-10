#!/usr/bin/env python
# coding: utf-8

# In[81]:


import geopandas as gpd
import requests
import time
import shapely
import geopandas_osm.osm
import numpy as np
import descartes as d
import math
import fiona
get_ipython().run_line_magic('matplotlib', 'inline')


# In[ ]:





# In[ ]:





# In[90]:


leftbound = -76.4092
rightbound = -76.3891
upperbound = -9.8721
lowerbound = -9.9083
bbox = [(leftbound,lowerbound ), (rightbound,lowerbound), (rightbound,upperbound), (leftbound,upperbound)]
poly = shapely.geometry.Polygon(bbox)
df = geopandas_osm.osm.query_osm('way', poly, recurse='down')
df.to_file("orig_map.shp")
df.plot()


# In[83]:


arr=["highway","residential", "primary", "secondary","tertiary","unclassified", "cycleway"]
df=df[df.highway.isin(arr)]
df["geometry"]


# In[ ]:





# In[102]:


newdata = gpd.GeoDataFrame()
newdata["street name"]=None
newdata["geometry"]=None
streetnewdata = gpd.GeoDataFrame()
streetnewdata["street name"]=None
streetnewdata["geometry"]=None
elev_point_data = gpd.GeoDataFrame()
elev_point_data["elevation"]=None
elev_point_data["geometry"]=None
junctions = gpd.GeoDataFrame()
junctions["geometry"]=None


# In[5]:


elevations = dict()


# In[6]:


print elevations


# In[37]:


all_coords_list = []
for geometry in df["geometry"]:
    for coord in geometry.coords:
        all_coords_list.append(coord)


# In[85]:


def is_intersection(val):
    num_matches = 0
    for i in all_coords_list:
        if val == i:
            num_matches +=1
    
    if(num_matches > 1):
        return True
    else:
        return False
def is_bend(coord, a, b):
    a = get_vector(a, coord)
    b = get_vector(b, coord)
    anorm = math.sqrt(dot(a, a))
    bnorm = math.sqrt(dot(b, b))
    theta = math.acos(dot(a, b)/(anorm*bnorm))
    if(theta > 1.57):
        return False
    else:
        return True
def get_elev_diff(point1, point2):
        return get_elev(point1)-get_elev(point2)
def get_elev(point):
    if(point in elevations):
        return elevations[point]
    else:
        rqstring = "https://maps.googleapis.com/maps/api/elevation/json?locations="+str(point[0])+","+str(point[1])
        elevation=requests.get(rqstring)
        try:
            elev = elevation.json()["results"][0]["elevation"]
            elevations[point] = elev
            time.sleep(.1)
            return elev
        except:
            print elevation.json()
            time.sleep(.1)
            return 0
        
def distance(point1, point2):
    return math.hypot(point2[0]-point1[0], point2[1]-point1[1])
def dot(a, b):
    return float((a[0]*b[0])+(a[1]*b[1]))
def get_vector(point, origin):
    return (point[0]-origin[0], point[1]-origin[1])
def get_anchor_point(point1, point2, elev_diff):
    xv = get_vector(point1, point2)[0]
    yv = get_vector(point1, point2)[1]
    anchor = (-yv, xv)
    anchor = [i*elev_diff/distance(point1, point2) for i in anchor] 
    return (point1[0]+anchor[0], point1[1]+anchor[1])
def reproject_segment(seg, anchor, end, elev_diff):
    #print "Beginning points: ",anchor, seg, end
    new_points = []
    distance_arr = []
    for point in seg:
        a = get_vector(point, anchor)
        b = get_vector(end, anchor)
        project_point = point
        try:
            c = dot(a, b)/dot(b,b)
        except:
            continue
        c = [c*i for i in b]
        p = (anchor[0]+c[0], anchor[1]+c[1])
        distance_arr.append(distance(p, anchor))
        cur_point_elev = get_elev(point)
        cur_point_elev_diff = round((cur_point_elev-max(elev1, elev2))*.001,7)
        p = get_anchor_point(p,end, cur_point_elev_diff)
        elev_point_data.loc[elev_point_data.shape[0]] = [cur_point_elev-max(elev1, elev2), shapely.geometry.point.Point(p)]
        new_points.append(p)
    
    zipped = zip(new_points, distance_arr)
    sorted_zip = sorted(zipped, key=lambda pair: pair[1])
    new_points = [a[0] for a in sorted_zip]
    new_points.insert(0, anchor)
    new_points.append(end)
    
    #print "Projected points: ", new_points
    return new_points


# In[ ]:





# In[ ]:





# In[ ]:





# In[106]:


new_index = -1
for index, geometry, name in zip(df.index.values, df["geometry"], df["name"]):
    new_index +=1
    coords = geometry.coords
    coords_list = [i for i in coords]
    intersection_list = [0]
    index=1
    for coord in coords[1:-1]:
        if(is_intersection(coord)):
            intersection_list.append(index)
        #elif(is_bend(coord, coords[0], coords[-1])):
        #    intersection_list.append(index)
        index+=1
    intersection_list.append(int(len(coords)-1))

    print "Length of intersection list:", len(intersection_list)
    if(len(intersection_list) >= 2):
        if(len(intersection_list) == 2):
            point1 = coords_list[intersection_list[0]]
            point2 = coords_list[intersection_list[1]]
            elev1 = get_elev(point1)
            elev2 = get_elev(point2)
            elev_diff=round((elev1-elev2)*.001,7)
            seg_arr = reproject_segment(coords_list[1:-2], point1, point2, elev_diff)
        else:
            prev_index = 0    
            for i in intersection_list[1:-1]:
                #print "section from point ", coords[prev_index], "to point", coords[i], ":",
                point1 = coords_list[prev_index]
                point2 = coords_list[i]
                elev1 = get_elev(point1)
                elev2 = get_elev(point2)
                elev_diff=round((elev1-elev2)*.0001,7)
                seg_arr = reproject_segment(coords_list[prev_index+1:i-1], point1, point2, elev_diff)
                prev_index = i

    else:
        elev_diff=round(get_elev_diff(coords[0], coords[1])*.001,7)
        seg_arr = coords_list  
        anchor = get_anchor_point(coords[0],coords[1], elev_diff)
        seg_arr.append(anchor)

    if(len(seg_arr) > 2):
        poly = shapely.geometry.Polygon(seg_arr[:][:])
        line = shapely.geometry.LineString(seg_arr[1:])
        try:
            newdata.loc[newdata.shape[0]] = [name, poly]
            streetnewdata.loc[streetnewdata.shape[0]] = [name, line]
            junctions.loc[junctions.shape[0]] = [shapely.geometry.point.Point(seg_arr[0])]
            junctions.loc[junctions.shape[0]] = [shapely.geometry.point.Point(seg_arr[-1])]
        except:
            continue


# In[ ]:





# In[93]:


base = streetnewdata.plot(color='white', edgecolor='black')
newdata.plot(ax=base, color='green');
df.plot(ax=base, color="orange")
for elev, point in zip(elev_point_data["elevation"][::50], elev_point_data["geometry"][::50]):
    base.annotate(str(round(elev*1000)), (point.x, point.y))


# In[ ]:





# In[112]:


import os
os.remove("out_map.geojson")
os.remove("out_street_map.geojson")
os.remove("out_elev_map.geojson")
os.remove("junctions.geojson")
newdata.to_file("out_map.geojson", driver="GeoJSON")
streetnewdata.to_file("out_street_map.geojson", driver="GeoJSON")
elev_point_data.to_file("out_elev_map.geojson", driver="GeoJSON")
junctions.to_file("junctions.geojson", driver="GeoJSON")


# In[ ]:





# In[ ]:





# In[ ]:



