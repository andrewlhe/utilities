%Initialize Workspace
clc
close all
clear all

%Prompt user input
prompt = 'Please enter amount (USD) to be transferred: ';
amount = linspace(10000,50000,81); %input(prompt);
prompt = 'Please enter the exchange rate (USD to CNY): ';
exchange_rate = linspace(7,7.5,101); %input(prompt);
prompt = 'Please enter the service fee rate (in thousands) : ';
serv_fee_rate = 1/1000; %input(prompt)/1000;
prompt = 'Please enter the maximum service fee (CNY): ';
max_serv_fee = 250; %input(prompt);
prompt = 'Please enter telegraph fee (CNY): ';
tele_fee = 80; %input(prompt);
prompt = 'Please enter incoming wire transfer fee (USD)? ';
income_fee = 16; %input(prompt);
prompt = 'Please enter fee charged by interchange bank (USD)? ';
interchange_fee = 18; %input(prompt);

serv_fee = zeros(81,101);
for i = 1:81
    for j = 1:101
        serv_fee(i,j) = amount(i) * exchange_rate(j) * serv_fee_rate;
        if serv_fee(i,j) > max_serv_fee
            serv_fee(i,j) = max_serv_fee;
        end
        serv_fee(i,j) = serv_fee (i,j) + tele_fee;
    end
end

fee = zeros(81,101);
fee_rate = zeros(81,101);
for i = 1:81
    for j = 1:101
        fee(i,j) = serv_fee(i,j) / exchange_rate(j) + income_fee + interchange_fee;
        fee_rate(i,j) = fee(i,j) / amount(i) * 1000;
    end
end

%disp(' ')
%A = ['The total fee for this transfer is $', num2str(fee), '.'];
%B = ['The fee rate is ', num2str(fee_rate), '/1000.'];
%disp(A)
%disp(B)