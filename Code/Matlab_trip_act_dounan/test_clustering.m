clc;
clear;
load('vij_0123_0206_2014.mat');
%a0=[];
%[a,b,c]=xlsread('5107250744_Vij_01232014.xlsx','B:D');
%a0=[a0;a];
%[a,b,c]=xlsread('5107250744_Vij_01242014.xlsx','B:D');
%a0=[a0;a];
%[a,b,c]=xlsread('5107250744_Vij_01252014.xlsx','B:D');
%a0=[a0;a];
%[a,b,c]=xlsread('5107250744_Vij_01262014.xlsx','B:D');
%a0=[a0;a];
%[a,b,c]=xlsread('5107250744_Vij_01272014.xlsx','B:D');
%a0=[a0;a];
%[a,b,c]=xlsread('5107250744_Vij_01282014.xlsx','B:D');
%a0=[a0;a];
%[a,b,c]=xlsread('5107250744_Vij_01302014.xlsx','B:D');
%a0=[a0;a];
%[a,b,c]=xlsread('5107250744_Vij_01312014.xlsx','B:D');
%a0=[a0;a];
%[a,b,c]=xlsread('5107250744_Vij_02042014.xlsx','B:D');
%a0=[a0;a];
%[a,b,c]=xlsread('5107250744_Vij_02062014.xlsx','B:D');
%a0=[a0;a];
%%
realdist=[];
realdist0=[];
testloc=a0(:,1:3);
%testloc=A{1,14}{2,1}(:,2:4);
timeloc0=testloc(:,1);
timeloc=testloc(:,1)-testloc(1,1);
realdist0=testloc(:,2:3);
realdist(:,1)=realdist0(:,1);
realdist(:,2)=realdist0(:,2);

tic;
[class,type]=act_trip_cluster_2([timeloc,realdist],3,20);
%[class,type]=dbscan([timeloc,realdist],6);
%[class,type]=dbscan(realdist,20,100);
toc

class_num=unique(class);
max_class=max(class_num)

h=figure(); 
set (gcf,'Position',[100,100,1000,1000], 'color','w')
set (gca,'position',[0.05,0.05,0.9,0.9] );

Latlim=[min(testloc(:,2)),max(testloc(:,2))];
Lonlim=[min(testloc(:,3)),max(testloc(:,3))];
plot(Lonlim,Latlim,'.w')
plot_google_map
hold on; 

plot3(realdist0(:,2),realdist0(:,1),timeloc);
hold on;
for i=1:length(class_num)

   current_class=class_num(i);
   index=find(class==current_class);
   if current_class<0
       plot3(realdist0(index,2),realdist0(index,1),timeloc(index),'.k','markersize',6);
       hold on;
   else
       index_c=find(class==current_class & type==1);
       index_b=find(class==current_class & type==0);
       plot3(realdist0(index_c,2),realdist0(index_c,1),timeloc(index_c),'.','markersize',10,'color',[mod(current_class,2),current_class/max_class,1-current_class/max_class]);
       hold on;
       plot3(realdist0(index_b,2),realdist0(index_b,1),timeloc(index_b),'.','markersize',10,'color',[mod(current_class,2),current_class/max_class,1-current_class/max_class]);
       hold on;
       text(realdist0(index(1),2),realdist0(index(1),1),timeloc(index(1)),[num2str(current_class),'-s']);
       hold on;
       text(realdist0(index(end),2),realdist0(index(end),1),timeloc(index(end)),[num2str(current_class),'-e']);
       hold on;
   end
    
end

ACT=cell(1,5); % activity logs

classtype=unique(class);
for i=1:length(classtype)-1
    ind=find(class==classtype(i+1));
    st=timeloc0(ind(1));
    et=timeloc0(ind(end));
    ACT{i,1}=timeloc0(ind(1)); %UTC milisecond
    ACT{i,2}=timeloc0(ind(end)); %UTC milisecond
    ACT{i,3}=datestr((st)/86400/1000 + datenum(1970,1,1)); %time str
    ACT{i,4}=datestr((et)/86400/1000 + datenum(1970,1,1)); %time str
    
    ind2=ind(1):ind(end);
    ACT{i,5}=[timeloc0(ind2),realdist0(ind2,1:2),type(ind2)'];
    
end


