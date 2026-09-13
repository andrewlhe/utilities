%Initialize Workspace
clc
close all
clear all

%Prompt user input
disp('Welcome to the Airline Miles Valuation and Elite Qualifying Miles Calculator!');
prompt = 'Please enter airline code (AA/DL/UA/WN/AS/B6/HA/AC): ';
Air_Line = input(prompt,'s');
prompt = 'Miles required for award: ';
Miles_Required = input(prompt);
prompt = 'Taxes and fees required for award: ';
Taxfee_a = input(prompt);
prompt = 'Cash price for the itinerary: ';
Cash = input(prompt);
prompt = 'Taxes and fees in the cash itinerary: ';
Taxfee_c = input(prompt);
prompt = 'Credit card cashback (%): ';
Cashback = input(prompt);
prompt = 'Flying Distance: ';
Distance = input(prompt);

%%Calculation
Miles_Accumulated = 0;
EQM = 0;

switch Air_Line
    %American Airlines
    case{'AA'}
        name = 'American Airlines';
        FFP_miles = 'AAdvantage mile';
        prompt = 'AA Elite status (Enter N-General Member, G-AAdvantage Gold,';
        prompt = [prompt newline 'P-AAdvantage Platinum, O-AAdvantage Platinum Pro, E-AAdvantage Executive Platinum): '];
        Elite = input(prompt,'s');
        prompt = 'AA Fare Class: ';
        Fare_class = input(prompt,'s');
        
        %Calculate Redeemable Miles (AAdvantage miles)
        switch Elite
            case{'N'}
                Miles_Accumulated = 5*(Cash-Taxfee_c);
            case{'G'}
                Miles_Accumulated = 7*(Cash-Taxfee_c);
            case{'P'}
                Miles_Accumulated = 8*(Cash-Taxfee_c);
            case{'O'}
                Miles_Accumulated = 9*(Cash-Taxfee_c);
            case{'E'}
                Miles_Accumulated = 11*(Cash-Taxfee_c);
        end
        
        %Calculate Elite Qualifying Miles
        switch Fare_class
            case{'B'} %Basic Economy
                EQM_Multiplier = 0.5;
            case{'Y','H','K','M','L','V','G','S','N','Q','O'} %Economy
                EQM_Multiplier = 1;
            case{'W','P'} %Premium Economy
                EQM_Multiplier = 1.5;
            case{'A','D','I','R'} %Discount First / Business
                EQM_Multiplier = 2;
            case{'F','J'} %Full Fare First / Business
                EQM_Multiplier = 3;
        end
        
        if Distance>500
            EQM = EQM_Multiplier*Distance;
        else 
            EQM = EQM_Multiplier*500;
        end 
        
    %Delta Air Lines    
    case{'DL'}
        name = 'Delta Air Lines';
        FFP_miles = 'Delta SkyMile';
        prompt = 'DL Elite status (Enter N-no status, S-Silver Medallion,';
        prompt = [prompt newline 'G-Gold Medallion, P-Platinum Medallion, D-Diamond Medallion): '];
        Elite = input(prompt,'s');
        prompt = 'DL Fare Class: ';
        Fare_class = input(prompt,'s');
        
        %Calculate Redeemable Miles (Delta Skymiles)
        switch Elite
            case{'N'}
                Miles_Accumulated = 5*(Cash-Taxfee_c);
            case{'S'}
                Miles_Accumulated = 7*(Cash-Taxfee_c);
            case{'G'}
                Miles_Accumulated = 8*(Cash-Taxfee_c);
            case{'P'}
                Miles_Accumulated = 9*(Cash-Taxfee_c);
            case{'D'}
                Miles_Accumulated = 11*(Cash-Taxfee_c);
        end
        
        %Calculate Medallion Qualification Miles
        switch Fare_class
            case{'W','M','S','H','Q','K','L','U','T','X','V','E'} %Comfort+, Economy, Discounted and Deeply Discounted Economy
                EQM_Multiplier = 1;
            case{'P','A','G','C','D','I','Z','Y','B'} %Discounted First, Premium Select, Business and Disounted Business, Full fare Economy
                EQM_Multiplier = 1.5;
            case{'F','J'} %First / Business
                EQM_Multiplier = 2;
        end
        
        if Distance>500
            EQM = EQM_Multiplier*Distance;
        else 
            EQM = EQM_Multiplier*500;
        end

    %United Airlines
    case{'UA'}
        name = 'United Airlines';
        FFP_miles = 'Mileageplus Mile';
        prompt = 'UA Elite status (Enter N-no status, S-Premier Silver,';
        prompt = [prompt newline 'G-Premier Gold, P-Premier Platinum, K-Premier 1K): '];
        Elite = input(prompt,'s');
        prompt = 'UA Fare Class (Enter N for Basic Economy): ';
        Fare_class = input(prompt,'s');
        
        %Calculate Redeemable Miles (Mileageplus Mileage)
        switch Elite
            case{'N'}
                Miles_Accumulated = 5*(Cash-Taxfee_c);
            case{'S'}
                Miles_Accumulated = 7*(Cash-Taxfee_c);
            case{'G'}
                Miles_Accumulated = 8*(Cash-Taxfee_c);
            case{'P'}
                Miles_Accumulated = 9*(Cash-Taxfee_c);
            case{'K'}
                Miles_Accumulated = 11*(Cash-Taxfee_c);
        end
    
        %Calculate Premier Qualifying Miles
        EQM_Multiplier = 0.5; %Default
        switch Fare_class
            case{'N'} %Basic Economy
                EQM_Multiplier = 0.5;    
            case{'M','E','U','H','Q','V','W','S','T','L','K','G'} %High/Discounted/Deep-Discounted/Lowest Discounted Economy
                EQM_Multiplier = 1;
            case{'P','O','A','R','Y','B'} %Deep-Discounted First/Business, High/Discounted/Deep-Discounted Premium Plus, Highest Full Fare/Full Fare Economy
                EQM_Multiplier = 1.5;    
            case{'C','D','Z'} %High/Discounted First/Business
                EQM_Multiplier = 2;   
            case{'J'} %Full Fare First/Business
                EQM_Multiplier = 3;   
        end
        
        if (Distance<500) && (strcmp(Elite,'S')||strcmp(Elite,'G')||strcmp(Elite,'P')||strcmp(Elite,'K'))  %Minimum 500 PQM for elite members
            EQM = EQM_Multiplier*500;
        else 
            EQM = EQM_Multiplier*Distance;
        end  
        
    %Southwest Airlines    
    case{'WN'}
        name = 'Southwest Airlines';
        FFP_miles = 'Rapid Rewards Point';
        prompt = 'WN Elite status (Enter N-no status, A-A-list, P-A-list Preferred): ';
        Elite = input(prompt,'s');
        prompt = 'WN Fare Class (Enter W-Wanna Get Away, A-Anytime, B-Business Select): ';
        Fare_class = input(prompt,'s');

        %Elite Status Multiplier
        Elite_Multiplier = 1; %%No status
        switch Elite
            case{'A'}
                Elite_Multiplier = 1.25; %%A-list
            case{'P'}
                Elite_Multiplier = 2; %%A-list Preferred (w/companion pass)
        end
        
        %Fare Class Multiplier
        Fare_Multiplier = 6;
        switch Fare_class
            case{'W'} %Wanna Get Away Earning
                Fare_Multiplier = 6;
            case{'A'} %Anytime Earning
                Fare_Multiplier = 10;
            case{'B'} %Business Select Earning
                Fare_Multiplier = 12;
        end 
        
        %Calculate Rapid Rewards Points and Tier Qualifying Points
        Miles_Accumulated = Elite_Multiplier*Fare_Multiplier*(Cash-Taxfee_c);
        EQM = Fare_Multiplier*(Cash-Taxfee_c);
    
    %Alaska Airlines    
    case('AS')
        name = 'Alaska Airlines';
        FFP_miles = 'MileagePlan mile';
        prompt = 'AS Elite status (Enter N-no status, M-MVP, G-MVP Gold, K-MVP Gold 75K): ';
        Elite = input(prompt,'s');
        prompt = 'AS Fare Class: ';
        Fare_class = input(prompt,'s');

        %Elite Status Bonus
        Elite_Bonus = 0;
        switch Elite
            case{'M'}
                Elite_Bouns = .5;
            case{'G'} 
                Elite_Bonus = 1;
            case{'K'}
                Elite_Bonus = 1.25;
        end
        
        %Fare class bonus
        Fare_Bonus = 0;
        switch Fare_class
            case{'H','Q','L','V','K','G','T','R','X'} %Main (Economy)
                Fare_Bonus = 0; 
            case{'M','B'} %Main (Economy)
                Fare_Bonus = 0.25;
            case{'Y','S'} %Main (Economy)
                Fare_Bonus = 0.5;
            case{'F','P','I'} %First Class
                Fare_Bonus = 0.75;
        end
        
        %Calculate MileagePlan Miles and Miles Towards Status
        if Distance>500
            Miles_Accumulated = (1 + Fare_Bonus + Elite_Bonus)*Distance;
        else
            Miles_Accumulated = (1 + Fare_Bonus + Elite_Bonus)*500;
        end
        EQM = (1+Fare_Bonus)*Distance; %Check this
        
    %Jetblue Airways    
    case('B6')
        name = 'Jetblue Airways';
        FFP_miles = 'TrueBlue point';
        prompt = 'B6 Elite status (Enter N-no status, M-Mosaic): ';
        Elite = input(prompt,'s');
        prompt = 'B6 Fare Class (Enter B-Blue, P-Blue Plus, F-Blue Flex, M-Mint): ';
        Fare_class = input(prompt,'s');
        
        %Calculate base flight points
        EQM = 3*(Cash-Taxfee_c);
        
        %Fare Class Multiplier for booking from Jetblue.com
        switch Fare_class
            case{'B','M'} %Blue and Mint
                Multiplier = 6;
            case{'P'} %Blue Plus
                Multiplier = 7;
            case{'F'} %Blue Flex
                Multiplier = 8;
        end
        
        %Calculate Trueblue Points
        switch Elite
            case{'N'}
                Miles_Accumulated = Multiplier*(Cash-Taxfee_c);
            case{'M'}
                Miles_Accumulated = (Multiplier+3)*(Cash-Taxfee_c);
        end
        
    %Hawaiian Airlines    
    case('HA')
        name = 'Hawaiian Airlines';
        FFP_miles = 'HawaiianMile';
        prompt = 'HA Elite status (Enter N-no status, C-Premier Club, G-Pualani Gold, P-Pualani Platinum): ';
        Elite = input(prompt,'s');
        prompt = 'HA Fare Class (Enter IC-Inter-Island Coach, IF-Inter-Island First,';
        prompt = [prompt newline 'C-NA and International Coach, F-NA First/International Business): '];
        Fare_class = input(prompt,'s');
        
        %Elite Status Multiplier
        Elite_Multiplier = 1;
        switch Elite
            case{'G'}
                Elite_Multiplier = 1.5;
            case{'P'}
                Elite_Multiplier = 2;
        end
        
        switch Fare_class
            case{'IC'} %Inter-island flights, 500 miles minimum for elite members
                EQM = 1*Distance;
                switch Elite
                    case{'N'}
                        Miles_Accumulated = Elite_Multiplier*Distance;
                    case{'C','G','P'}
                        Miles_Accumulated = Elite_Multiplier*500;
                end
            case{'IF'} %Inter-island flights, 500 miles minimum for elite members
                EQM = 1.5*Distance;                
                switch Elite
                    case{'N'}
                        Miles_Accumulated = 1.5*Elite_Multiplier*Distance;
                    case{'C','G','P'}
                        Miles_Accumulated = Elite_Multiplier*500;
                end
            case{'C'} %North America/International coach
                EQM = 1*Distance;
                Miles_Accumulated = Elite_Multiplier*Distance;
            case{'F'} %North America First Class/International Business
                EQM = 1.5*Distance;                
                Miles_Accumulated = 1.5*Elite_Multiplier*Distance;
        end
        
    %Air Canada
    case{'AC'}
        name = 'Air Canada';
        FFP_miles = 'Aeroplan mile';
        prompt = 'AC Elite status (Enter N-no status, P-Prestige 25K, E3-Elite 35K,';
        prompt = [prompt newline 'E5-Elite 50K, E7-Elite 75K, S-Super Elite 100K): '];
        Elite = input(prompt,'s');
        prompt = 'AC Travel Region (Enter C-Within Canada, U-Between Canada and US,';
        prompt = [prompt newline 'S-Between Canada and Carribbean, Mexico and Central America, I-Between Canada and international destinations): '];
        Region = input(prompt,'s');
        prompt = 'AC Fare Class: ';
        Fare_class = input(prompt,'s');
        prompt = 'If Economy, select fare option (Enter C-Comfort, F-Flex, S-Standard, B-Economy Basic): '; 
        Fare_option = input(prompt,'s');
        
        %Elite Status Multiplier
        Elite_Multiplier = 1;
        switch Elite
            case{'P'}
                Elite_Multiplier = 1.25;
            case{'E3'}
                Elite_Multiplier = 1.35;
            case{'E5'}
                Elite_Multiplier = 1.5;
            case{'E7'}
                Elite_Multiplier = 1.75;
            case{'S'}
                Elite_Multiplier = 2;
        end
        
        switch Region
            
            %Within Canada
            case{'C'} 
                
                %Fare Multiplier for flights within Canada
                switch Fare_class
                    case{'J','C','D','Z','P'} %Business class (flexible/lowest)/Premium Rouge
                        Fare_Multiplier = 1.5;
                    case{'O','E','N','Y','B'}%Premium economy (flexible/lowest)/Latitude
                        Fare_Multiplier = 1.25;
                    case{'M','U','H','Q','V','W','S','T','L','A','K','F'}%Economy
                        switch Fare_option
                        	case{'C'}%Comfort
                            	Fare_Multiplier = 1.15;
                        	case{'F'}%Flex
                            	Fare_Multiplier = 1;
                        	case{'S'}%Standard
                            	Fare_Multiplier = .25;
                        	case{'B'}%Basic Economy
                             	Fare_Multiplier = 0;
                        end
                end
                
                switch Elite
                    case{'N'} %General Members don't have minimum 250 miles
                        Miles_Accumulated = Fare_Multiplier*Distance;
                        EQM = Fare_Multiplier*Distance;
                    case{'P','E3','E5','E7','S'} %Elite Members have minimum 250 miles per segment
                        if Distance>250
                            Miles_Accumulated = Elite_Multiplier*Fare_Multiplier*Distance;
                            EQM = 1.5*Distance;
                        else 
                            Miles_Accumulated = Elite_Multiplier*Fare_Multiplier*250;
                            EQM = 1.5*250;
                        end 
                end
            
            %Between Canada and United States
            case{'U'} 
                
                %Fare Multiplier for flights between Canada and United States
                switch Fare_class
                    case{'J','C','D','Z','P'} %Business class (flexible/lowest)/Premium Rouge
                        Fare_Multiplier = 1.5;
                    case{'O','E','N','Y','B'} %Premium economy (flexible/lowest)/Latitude
                        Fare_Multiplier = 1.25;
                    case{'M','U','H','Q','V','W','S','T','L','A','K','F'} %Economy
                        switch Fare_option
                        	case{'C'}%Comfort
                            	Fare_Multiplier = 1.15;
                        	case{'F'}%Flex
                            	Fare_Multiplier = 1;
                        	case{'S'}%Standard
                            	Fare_Multiplier = .5;
                        	case{'B'}%Basic Economy
                             	Fare_Multiplier = 0;
                        end
                end
                
                switch Elite
                    case{'N'} %General Members don't have minimum 250 miles
                        Miles_Accumulated = Fare_Multiplier*Distance;
                        EQM = Fare_Multiplier*Distance;    
                    case{'P','E3','E5','E7','S'} %Elite Members have minimum 250 miles per segment
                        if Distance>250
                            Miles_Accumulated = Elite_Multiplier*Fare_Multiplier*Distance;
                            EQM = 1.5*Distance;
                        else 
                            Miles_Accumulated = Elite_Multiplier*Fare_Multiplier*250;
                            EQM = 1.5*250;
                        end 
                end
                
            %Between Canada and sun destinations (Carribean, Mexico, and Central America)
            case{'S'} 
                
                %Fare Multiplier for flights between Canada and sun destinations
                switch Fare_class
                    case{'J','C','D','Z','P'} %Business class (flexible/lowest)/Premium Rouge
                        Fare_Multiplier = 1.5;
                    case{'O','E','N','Y','B'}%Premium economy (flexible/lowest)/Latitude
                        Fare_Multiplier = 1.25;
                    case{'M','U','H','Q','V','W','S','T','L','A','K','F'}%Economy
                        switch Fare_option
                        	case{'C'}%Comfort
                            	Fare_Multiplier = 1.15;
                        	case{'F'}%Flex
                            	Fare_Multiplier = 1;
                        	case{'S'}%Standard
                            	Fare_Multiplier = .5;
                        end
                end
                
                Miles_Accumulated = Elite_Multiplier*Fare_Multiplier*Distance;
                EQM = Fare_Multiplier*Distance;
            
            %Between Canada and other international destinations    
            case{'I'} 
                
                %Fare Multiplier for flights between Canada and other international destinations 
                switch Fare_class
                    case{'J','C','D','Z','P'} %Business class (flexible/lowest)/Premium Rouge
                        Fare_Multiplier = 1.5;
                    case{'O','E','N','Y','B'} %Premium economy (flexible/lowest)/Latitude
                        Fare_Multiplier = 1.25;
                    case{'M','U','H','Q','V','W','S','T','L','A','K','F'} %Economy
                        switch Fare_option
                        	case{'F'}%Flex
                            	Fare_Multiplier = 1;
                        	case{'S'}%Standard
                            	Fare_Multiplier = .5;
                        	case{'B'}%Basic Economy
                             	Fare_Multiplier = .25;
                        end
                end
                
                Miles_Accumulated = Elite_Multiplier*Fare_Multiplier*Distance;
                EQM = Fare_Multiplier*Distance;
        end 
end

Total_Miles = Miles_Accumulated + Miles_Required;
CPM = (Cash-Taxfee_a)*(1-Cashback/100)/Total_Miles*100;
CPEQM = Cash/EQM*100;

disp(' ')
A=['This award ticket from ', name, ' requires ', num2str(Miles_Required), ' ', FFP_miles,'s. '];
B=['At a cash price of $',num2str(Cash), ', each ', FFP_miles, ' is worth ', num2str(CPM), ' cents.'];
C=['The cash fare can also earn ', num2str(EQM), ' elite qualifying miles/points for ', name, '. '];
D=['For this flight, each elite qualifying mile/point is worth ', num2str(CPEQM), ' cents.'];

disp(A)
disp(B)
disp(C)
disp(D)