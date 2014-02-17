%6,9,13
ind=find(class==2);
realdist_home=realdist(1:ind(end),:);
%ind=randi(length(realdist_home0),1000,1);
%realdist_home=realdist_home0(ind,:);
figure
plot(realdist_home(:,1),realdist_home(:,2),'.');
loc_home=median(realdist_home);
loc_home2=mean(realdist_home);

D=sqrt(sum((((ones(size(realdist_home,1),1)*median(realdist_home))-realdist_home).^2)'));
hold on
plot(loc_home(1),loc_home(2),'*r','markersize',10);
hold on
plot(loc_home2(1),loc_home2(2),'+y','markersize',10);

figure()
hist3(realdist_home,[100,100]);
%% 
figure()
[N,zb]=hist3(realdist_home,[100,100]);
[X,Y]=meshgrid(zb{2},zb{1});
contour(Y,X,N,10);
hold on
plot3(loc_home(1),loc_home(2),2,'.r','markersize',20);
hold on
plot3(loc_home2(1),loc_home2(2),2,'.y','markersize',20);
%%
figure
xMaxima=D;
paramEstsMaxima = evfit(-xMaxima);
y = linspace(min(D),max(D),1001);
[N,X]=hist(xMaxima,min(D):.25:max(D));
h1=bar(X,N,'hist');
set(h1,'edgecolor','none')
p = evpdf(-y,paramEstsMaxima(1),paramEstsMaxima(2));
line(y,.25*length(xMaxima)*p,'color','r','linewidth',2)
axis([min(D),max(D),0,max(N)+10]) 
title(['mu=',num2str(-paramEstsMaxima(1)),'; bata=',num2str(paramEstsMaxima(2))]);