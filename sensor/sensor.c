#include <wiringPi.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <hiredis.h>

#define MAX_TIME 85
#define DHT11PIN 8

typedef unsigned char uchar;

int dht11_val[5];
uchar LED8_PIN[8] = {14, 13, 12, 3, 2, 0, 7, 9}; /* A B C D E F G H */

redisContext *c;
redisReply *reply;
char str[8];

void dht11_read_val();
uchar trans(uchar n);
void display(uchar n1, uchar n2, uchar n3, uchar n4);

int main(void)
{
  int j;

  c = redisConnect("127.0.0.1", 6379);
  if (c != NULL && c->err)
  {
    printf("Error: %s\n", c->errstr);
  }

  if (wiringPiSetup() == -1)
  {
    exit(1);
  }
  for (j = 0; j < 8; ++j)
  {
      pinMode(LED8_PIN[j], OUTPUT);
      digitalWrite(LED8_PIN[j], HIGH);
  }

  while (1)
  {
    dht11_read_val();
  }

  redisFree(c);
  return 0;
} 

void dht11_read_val()
{
  uint8_t lststate = HIGH;
  uint8_t counter = 0;
  uint8_t j = 0, i = 0;
  uchar n, n1, n2, n3, n4;

  for (i = 0; i < 5; ++i)
  {
    dht11_val[i]=0;
  }
  /* 开始信号 */
  pinMode(DHT11PIN, OUTPUT);
  digitalWrite(DHT11PIN, LOW);
  delay(18);
  digitalWrite(DHT11PIN, HIGH);
  delayMicroseconds(40);
  /* 开始读取数据 */
  pinMode(DHT11PIN, INPUT);
  for (i = 0; i < MAX_TIME; ++i)
  {
    /* 循环延时等待数据 */
    counter = 0;
    while (digitalRead(DHT11PIN) == lststate)
    {
      ++counter;
      delayMicroseconds(1);
      if (counter == 255)
      {
        break;
      }
    }
    lststate = digitalRead(DHT11PIN);
    if (counter == 255)
    {
       break;
    }
    // top 3 transistions are ignored
    if ((i >= 4) && (i % 2 == 0))
    {
      dht11_val[j / 8] <<= 1;
      if (counter > 16)
      {
        dht11_val[j / 8] |= 1;
      }
      ++j;
    }
  }
  // verify cheksum and print the verified data
  if ((j >= 40) && (dht11_val[4] == ((dht11_val[0] + dht11_val[1] + dht11_val[2] + dht11_val[3]) & 0xFF)))
  {
    printf("当前温度：%d.%d°C\t当前湿度： %d.%d%\n", dht11_val[2], dht11_val[3], dht11_val[0], dht11_val[1]);
    memset(str, 0x00, sizeof(str));
    sprintf(str, "%d", dht11_val[2]);
    reply = redisCommand(c, "SET %s %s", "temperature", str);
    // printf("SET: %s\n", reply->str);
    freeReplyObject(reply);
    memset(str, 0x00, sizeof(str));
    sprintf(str, "%d", dht11_val[0]);
    reply = redisCommand(c, "SET %s %s", "humidity", str);
    // printf("SET: %s\n", reply->str);
    freeReplyObject(reply);

    n = dht11_val[2];
    n2 = n % 10;
    n /= 10;
    n1 = n % 10;
    n = dht11_val[0];
    n4 = n % 10;
    n /= 10;
    n3 = n % 10;
    display(n1, n2, n3, n4);
  }
}

uchar trans(uchar n)
{
  switch (n)
  {
    case 0:
        return 0XFC;/*11111100*/
    case 1:
        return 0X60;/*01100000*/
    case 2:
        return 0XDA;/*11011010*/
    case 3:
        return 0XF2;/*11110010*/
    case 4:
        return 0X66;/*01100110*/
    case 5:
        return 0XB6;/*10110110*/
    case 6:
        return 0XBE;/*10111110*/
    case 7:
        return 0XE0;/*11100000*/
    case 8:
        return 0XFE;/*11111110*/
    case 9:
        return 0XF6;/*11110110*/
    case 10:
        return 0X02;/*00000010*/
    case 11:
        return 0X00;/*00000010*/
  }
}

void display(uchar n1, uchar n2, uchar n3, uchar n4)
{
  uchar i, j, k, nn[6];

  nn[0] = trans(n1);
  nn[1] = trans(n2);
  nn[2] = trans(n3);
  nn[3] = trans(n4);
  nn[4] = trans(10);
  nn[5] = trans(11);

  for (k = 0; k < 4; ++k)
  {
    if (k == 2)
    {
      i = 8;
      while (i)
      {
        pinMode(LED8_PIN[8 - i], OUTPUT);
        j = (nn[4] >> (i - 1)) & 1;
        if (j == 1)
        {
          digitalWrite(LED8_PIN[8 - i], LOW);
        }
        else
        {
          digitalWrite(LED8_PIN[8 - i], HIGH);
        }
        --i;
      }
      delay(500);
    }
    if (k == 0)
    {
      i = 8;
      while (i)
      {
        pinMode(LED8_PIN[8 - i], OUTPUT);
        j = (nn[5] >> (i - 1)) & 1;
        if (j == 1)
        {
          digitalWrite(LED8_PIN[8 - i], LOW);
        }
        else
        {
          digitalWrite(LED8_PIN[8 - i], HIGH);
        }
        --i;
      }
      delay(500);
    }

    i = 8;
    while (i)
    {
      pinMode(LED8_PIN[8 - i], OUTPUT);
      j = (nn[k] >> (i - 1)) & 1;
      if (j == 1)
      {
        digitalWrite(LED8_PIN[8 - i], LOW);
      }
      else
      {
        digitalWrite(LED8_PIN[8 - i], HIGH);
      }
      --i;
    }
    delay(500);
  }
}
