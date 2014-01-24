#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <hiredis.h>

redisContext *c;
redisReply *reply;

int main(void)
{
  int j;

  c = redisConnect("127.0.0.1", 6379);
  if (c != NULL && c->err)
  {
    printf("Error: %s\n", c->errstr);
  }

  reply = redisCommand(c,"GET temperature");
  printf("GET temperature: %s\n", reply->str);
  freeReplyObject(reply);

  reply = redisCommand(c,"GET humidity");
  printf("GET humidity: %s\n", reply->str);
  freeReplyObject(reply);

  redisFree(c);
  return 0;
} 
