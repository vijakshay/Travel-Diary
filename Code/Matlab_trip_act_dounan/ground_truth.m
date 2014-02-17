[a,b,c]=xlsread('vij_0123_0206_groundtruth.xlsx');
C=c(2:end,:);
time_matric=zeros(6,1);
for i=1:size(C,1)
    if length(C{1,19})==4
        tempstr0=C{i,1};
    else
        tempstr0=C{i,19};
    end
    tempstr=regexp(tempstr0,' ' ,'split');
    timestr=[tempstr{3},'-',tempstr{2},'-',tempstr{6},' ',tempstr{4}];
    %'08-Jun-2004 00:31:37'   'vector'   [2004 6 8 0 31 37]
    time_matric(i,1:6)=DateConvert(timestr, 'vector');
    
    time_matric(i,7)=DateConvert(timestr, 'number');
    time_matric(i,11)=(time_matric(i,7)-datenum(1970,1,1))*24*3600*1000;
    if length(C{i,6})==4
        time_matric(i,8)=-1;
    else  
        time_matric(i,8)=1;
    end
    time_matric(i,9)=C{i,14};
    time_matric(i,10)=C{i,15};
end

[s ind]=sort(time_matric(:,7));
G=time_matric(ind,:);
n=1;
class_g=ones(size(a0,1),1)*(-1);
for i=1:size(G,1)
   if G(i,8)>0
       st=G(i,11);
       et=G(i+1,11);
       ind=find(a0(:,1)>=st & a0(:,1)<et);
       class_g(ind)=n;
       n=n+1;
   end    
end
%%

CM=zeros(2,2);

ind_a_e=find(class'>0);
ind_t_e=find(class'<0);
ind_a_g=find(class_g>0);
ind_t_g=find(class_g<0);

CM(1,1)=length(intersect(ind_a_e,ind_a_g));
CM(1,2)=length(intersect(ind_t_e,ind_a_g));

CM(2,1)=length(intersect(ind_a_e,ind_t_g));
CM(2,2)=length(intersect(ind_t_e,ind_t_g));