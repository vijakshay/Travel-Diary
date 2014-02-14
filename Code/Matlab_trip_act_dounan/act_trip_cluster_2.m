
% -------------------------------------------------------------------------
% Function: [class,type]=act_trip_cluster_2(data,min_time,Eps)
% -------------------------------------------------------------------------
% Aim: 
% Clustering the data into activities and trips with Density-Based Scan
% Algorithm with Noise (DBSCAN) in time windows
% -------------------------------------------------------------------------
% Input: 
% data - m*3 matric [UTC milisec, lat, lng]
% min_time - minimal time for an activity, unit: min (3 min suggusted) 
% Eps - neighborhood radius, (meters) if not known avoid this parameter or
% put []
% -------------------------------------------------------------------------
% Output: 
% class - vector specifying assignment of the i-th object to certain 
% cluster (m,1), -1 for trips, positive value for different activities
% type - vector specifying type of the i-th object 
% (core: 1, border: 0, outlier: -1) 
% -------------------------------------------------------------------------
% Written by Dounan Tang
% Feb. 2014
% dounan.tang@berkeley.edu

function [class,type]=act_trip_cluster_2(data,min_time,Eps)

time_thre=min_time*60*1000;
num_thre=2; % density threshold for outliers
time_vec=data(:,1); 

x=data(:,2:3);

%% convert [lat, lng] into meters in central CA
x(:,1)=x(:,1)*89.7*1000; 
x(:,2)=x(:,2)*112.7*1000;

%% calucate the median time interval for time_vec and set up minimal numbers of pnts for an activitym,k, and number of pnts for time windows,time_windows

time_interval=median(time_vec(2:end)-time_vec(1:end-1));
k=round(time_thre/time_interval);
time_windows=round(time_thre/time_interval*2); % here 2 is an amplification factor of k

%% mian 
[m,n]=size(x);

if isempty(Eps)
   [Eps]=epsilon(x,k);
   %Eps/1000
end

%Eps

x=[[1:m]' x];
[m,n]=size(x);
type=zeros(1,m);
no=1;
touched=zeros(m,1);

for i=1:m
    if touched(i)==0;
       ob=x(i,:);
    %   ob_time=time_vec(i);
       ind0=i:(min(i+time_windows,m));
       D=dist(ob(2:n),x(ind0,2:n)); 
       ind1=ind0(find(D<=Eps));
       ind=ind1(find(touched(ind1)==0));
       
       if length(ind)>num_thre & length(ind)<k+1       
          type(i)=0;
          class(i)=0;
       end
       if length(ind)<=num_thre
          type(i)=-1;
          class(i)=-1;  
          touched(i)=1;
       end

       if length(ind)>=k+1; 
          type(i)=1;
          class(ind)=ones(length(ind),1)*max(no);
          
          while ~isempty(ind)
                ob=x(ind(1),:); %maybe not needed
                %ob_time=time_vec(ind(1));
                touched(ind(1))=1;
                i10=ind(1):(min(ind(1)+time_windows,m));
                D=dist(ob(2:n),x(i10,2:n));
                i1=i10(find(D<=Eps));
                
                ind(1)=[]; 
                
                if length(i1)>num_thre
                   class(i1)=no;
                   if length(i1)>=k+1;
                      type(ob(1))=1;
                   else
                      type(ob(1))=0;
                   end

                   for ii=1:length(i1)
                       if touched(i1(ii))==0
                          touched(i1(ii))=1;
                          if isempty(find(ind==i1(ii)))
                            ind=[ind i1(ii)];
                          end
                          %length(ind)==length(unique(ind))
                          class(i1(ii))=no;
                       end                    
                   end
                end
          end
          no=no+1; 
       end
       
   end
end

i1=find(class==0);
class(i1)=-1;
type(i1)=-1;


%...........................................
function [Eps]=epsilon(x,k)

% Function: [Eps]=epsilon(x,k)
%
% Aim: 
% Analytical way of estimating neighborhood radius for DBSCAN
%
% Input: 
% x - data matrix (m,n); m-objects, n-variables
% k - number of objects in a neighborhood of an object
% (minimal number of objects considered as a cluster)



[m,n]=size(x);

Eps=((prod(max(x)-min(x))*k*gamma(.5*n+1))/(m*sqrt(pi.^n))).^(1/n);


%............................................
function [D]=dist(i,x)

% function: [D]=dist(i,x)
%
% Aim: 
% Calculates the Euclidean distances between the i-th object and all objects in x	 
%								    
% Input: 
% i - an object (1,n)
% x - data matrix (m,n); m-objects, n-variables	    
%                                                                 
% Output: 
% D - Euclidean distance (m,1)



[m,n]=size(x);
if n==1
    D=abs((ones(m,1)*i-x))';
else
    D=sqrt(sum((((ones(m,1)*i)-x).^2)'));
end
