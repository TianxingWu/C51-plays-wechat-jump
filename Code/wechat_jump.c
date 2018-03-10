#include<reg52.h>
#define uchar unsigned char
#define uint unsigned int

/* 特殊位定义 */
sbit dula = P2^6;
sbit wela = P2^7;

/* 数码管编码表 */
uchar code table[]={
0x3f, 0x06, 0x5b, 0x4f, 
0x66, 0x6d, 0x7d, 0x07,
0x7f, 0x6f, 0x77, 0x7c,
0x39, 0x5e, 0x79, 0x71, 0};

/* 全局变量定义 */
uint press_time, TIME_BASE;
uchar flag, numL, numH;

/* 函数声明 */
void init();
void display(uint);
void delay(uint);

/* 主函数 */
void main()
{
	//一、初始化
	init();
	
	//二、进入主循环
	while(1)
	{
		//1.读取串口时长数据
		while(!RI);
		RI = 0;
		numL = SBUF;	//从缓存区取出低8位
		
		while(!RI);
		RI = 0;
		numH = SBUF;	//从缓存区取出高8位
		press_time = (numH<<8)|numL;	//组装成16位
		
		//2.按照读取的时长进行倒计时，期间数码管显示时长、P1^0口置0
		TR0 = 1;	//开启定时器
		while(TIME_BASE<press_time)
		{
			display(press_time);
			P1 = 0xFE;
		}
		TR0 = 0;	//关闭定时器
		
		//3.复位
		TIME_BASE = 0;
		P1 = 0xFF;
		dula = 1;
		P0 = table[16];
		dula = 0;
	}
}


/* 初始化函数 */
void init()
{
	/* 初始化锁存器 */
	dula = 0;
	wela = 0;
	
	/* 初始化定时器1 */
	//设置定时器1为工作方式2，定时器0为工作方式1
	TMOD = 0x21;
	//给定时器1装初值，波特率为9600bps
	TH1 = 0xFD;
	TL1 = 0xFD;
	//启动定时器1
	TR1 = 1;
	
	/* 初始化定时器0 */
//	TMOD = 0x01;	//设置定时器0工作方式
	TH0 = (65536-922)/256;	//给初值的高位赋值 定时1ms 晶振：11.0592MHZ
	TL0 = (65536-922)%256;	//给初值的低位赋值
	EA = 1;		//开总中断
	ET0 = 1;	//开定时器0中断
	TR0 = 0;	//关闭定时器0
	TIME_BASE = 0;	//初始化变量TIME_BASE

	/* 初始化串口 */
	//设置串口为工作方式1
	SM0 = 0;
	SM1 = 1;
	//允许串口接收数据
	REN = 1;
}



/* 数码管动态显示函数 */
void display(uint number)
{
	uchar qian;
	uchar bai;
	uchar shi;
	uchar ge;
	
	if (number>999)
	{
		qian = number/1000;
		bai = number%1000/100;
		shi = number%1000%100/10;
		ge = number%10;
		
		//千位
		dula = 1;
		P0 = table[qian];
		dula = 0;
		P0 = 0xFF;	//消影
		wela = 1;
		P0 = 0xFE;
		wela = 0;
		delay(1);
		
		//百位
		dula = 1;
		P0 = table[bai];
		dula = 0;
		P0 = 0xFF;	//消影
		wela = 1;
		P0 = 0xFD;
		wela = 0;
		delay(1);
		
		//十位
		dula = 1;
		P0 = table[shi];
		dula = 0;
		P0 = 0xFF;	//消影
		wela = 1;
		P0 = 0xFB;
		wela = 0;
		delay(1);
		
		//个位
		dula = 1;
		P0 = table[ge];
		dula = 0;
		P0 = 0xFF;	//消影
		wela = 1;
		P0 = 0xF7;
		wela = 0;
		delay(1);
	}
	
	else if (number>99)
	{
		bai = number/100;
		shi = number%100/10;
		ge = number%10;
		
		//百位
		dula = 1;
		P0 = table[bai];
		dula = 0;
		P0 = 0xFF;	//消影
		wela = 1;
		P0 = 0xFE;
		wela = 0;
		delay(1);
		
		//十位
		dula = 1;
		P0 = table[shi];
		dula = 0;
		P0 = 0xFF;	//消影
		wela = 1;
		P0 = 0xFD;
		wela = 0;
		delay(1);
		
		//个位
		dula = 1;
		P0 = table[ge];
		dula = 0;
		P0 = 0xFF;	//消影
		wela = 1;
		P0 = 0xFB;
		wela = 0;
		delay(1);
	}
	
	else if (number>9)
	{
		shi = number/10;
		ge = number%10;
		
		//十位
		dula = 1;
		P0 = table[shi];
		dula = 0;
		P0 = 0xFF;	//消影
		wela = 1;
		P0 = 0xFE;
		wela = 0;
		delay(1);
		
		//个位
		dula = 1;
		P0 = table[ge];
		dula = 0;
		P0 = 0xFF;	//消影
		wela = 1;
		P0 = 0xFD;
		wela = 0;
		delay(1);
	}
	
	else
	{
		dula = 1;
		P0 = table[number];
		dula = 0;
		P0 = 0xFF;	//消影
		wela = 1;
		P0 = 0xFE;
		wela = 0;
		delay(1);
	}
}


/* 延时函数 */
void delay(uint time)
{
	uint x,y;
	for (x=time; x>0; x--)
		for (y=114; y>0; y--);
}


/* 定时器中断服务程序 */
void Time0() interrupt 1
{
	TH0 = (65536-922)/256;	//重装初值
	TL0 = (65536-922)%256;
	TIME_BASE++;	//每过1ms，TIME_BASE加1
}