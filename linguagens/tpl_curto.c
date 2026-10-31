/* TPL - medicao curta (Golden Gate) em C. Mesmo calculo do tpl_curto.py.
   Compile e rode: gcc -O0 -o tpl_curto tpl_curto.c -lm && ./tpl_curto */
#include <stdlib.h>
#include "sha256.h"
static double round_n(double x, int n){ char s[64]; snprintf(s,sizeof s,"%.*f",n,x); return strtod(s,NULL); }
int main(void){
  int vao_central=1280, vao_lateral=343, torre_agua=227, torre_pista=152;
  int pista = torre_agua - torre_pista;
  int flecha = torre_pista - 6;
  double razao = (double)vao_lateral / (double)vao_central;
  double flecha_lat = flecha * (razao * razao);
  double cabo[33]; int i, imin=0, simetrico=1;
  for(i=0;i<33;i++) cabo[i]=round_n(torre_agua - 4.0*flecha*((double)i/32)*(1-(double)i/32), 3);
  for(i=1;i<33;i++) if(cabo[i]<cabo[imin]) imin=i;
  for(i=0;i<33;i++) if(cabo[i]!=cabo[32-i]) simetrico=0;
  char a[40], b[40], c[40], texto[512], h[65];
  repr_float(cabo[imin], a); repr_float(round_n(flecha_lat,3), b); repr_float(round_n(razao,6), c);
  snprintf(texto,sizeof texto,"{\"cabo_minimo_m\": %s, \"cabo_minimo_no_meio\": \"%s\", \"cabo_simetrico\": \"%s\", \"flecha_central_m\": %d, \"flecha_lateral_m\": %s, \"lateral_sobre_central\": %s, \"pista_m\": %d}",
           a, imin==16?"SIM":"NAO", simetrico?"SIM":"NAO", flecha, b, c, pista);
  sha256_hex(texto, strlen(texto), h);
  printf("%s\nresultado_sha256: %s\n", texto, h);
  return 0;
}
