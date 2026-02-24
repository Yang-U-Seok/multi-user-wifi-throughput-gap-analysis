# multi-user-wifi-throughput-gap-analysis
- 다중 사용자 환경에서 Wi-Fi의 이론적 처리량과 실제 측정 처리량 간의 성능 격차를 정량적으로 분석하고, 그 원인을 이론적 모델과 실험 데이터를 기반으로 규명한다.

## Motivation
- 실제로 한 Wi-Fi에는 여러 사용자가 접속하여 인터넷에 연결하는 경우가 많으며 한 기기만 연결하는 일은 드물다.
- 그러나 여러 기기를 연결할수록 사용자가 체감하는 처리량은 감소하며 한 기기만을 사용했을 때와의 성능 차이가 발생한다.
- 본 프로젝트는 이론적 처리량과 실제로 측정된 처리량 간의 성능 격차를 통신 계층 관점에서 분석하고 그 원인을 규명하는 것을 목표로 한다.
  
## Overview
- 단일 사용자 환경과 다중 사용자 환경에서의 Wi-Fi 처리량을 비교 분석한다.
- Shannon capacity 및 PHY link rate를 기반으로 이론적 상한을 정의한다.
- 실제 패킷 캡처 데이터를 활용하여 측정 처리량을 산출하고, 이론값과의 차이를 정량적으로 평가한다.
- 채널 경쟁, 프로토콜 오버헤드, 재전송 등의 요인이 처리량 감소에 미치는 영향을 분석한다.

---

## Theoretical Model

- 이상적인 무선 채널 환경에서 달성 가능한 최대 전송률은 Shannon capacity로 표현된다.

$$
C = B \log_2(1 + SNR)
$$

여기서 **C**는 채널 용량(Channel Capacity), **B**는 채널 대역폭(Bandwidth), **SNR**은 신호 대 잡음비(Signal-to-Noise Ratio, S/N)를 의미한다.

이 값은 물리 계층에서 달성 가능한 정보이론적 상한이며, 실제 Wi-Fi 프로토콜 오버헤드나 채널 경쟁은 고려하지 않는다.

- 이상적인 다중 사용자 환경에서 한 사용자가 이론적으로 달성 가능한 최대 전송률은 다음과 같이 정의된다.

$$
T_{\text{ideal,shannon}} = \frac{C}{N}
$$

이는 정보이론적 상한을 사용자 수로 나눈 값으로, 현실적인 무선 환경에서는 직접적으로 달성되기 어렵다.

---

## Measurement Model

- 실제 처리량은 PCAP 기반 패킷 캡처 데이터에서 측정 구간 $\Delta t$ 동안 관측된 프레임 길이의 합을 이용해 계산한다.

$$
T_{\text{measured}}=\frac{\sum(\text{frame.len}\times 8)}{\Delta t}
$$

여기서 `frame.len`은 MAC 및 상위 계층 헤더를 포함한 전체 프레임 길이를 의미한다.

---

## GAP 정의

본 연구에서 성능 격차는 다음과 같이 정의한다.

$$
G = T_{\text{ideal,phy}} - T_{\text{measured}}
$$

또한, PHY 기반 이론 상한 대비 실제 효율은 다음과 같이 정의한다.

$$
\eta = \frac{T_{\text{measured}}}{T_{\text{ideal,phy}}}
$$

---

## Theoretical Experiment (PHY 기반 상한)

- Receive link rate: 135 Mbps  
- Transmit link rate: 300 Mbps  
- Band: 2.4 GHz (802.11n)

본 연구에서는 수신 링크 속도(135 Mbps)를 실험 비교를 위한 실용적 이론 상한으로 사용한다.

$$
T_{\text{ideal,phy}} = \frac{R_{\text{phy}}}{N}
$$

### Case 1 (N = 1)
$$
T_{\text{ideal,phy}} = 135 \text{ Mbps}
$$

### Case 2 (N = 2)
$$
T_{\text{ideal,phy}} = 67.5 \text{ Mbps}
$$

### Case 3 (N = 3)
$$
T_{\text{ideal,phy}} = 45 \text{ Mbps}
$$

---

## Measured Experiment (Speedtest 기반)

### N = 1
Measured Throughput: **57.03 Mbps**

### N = 2
Measured Throughput: **25.59 Mbps**

### N = 3
Measured Throughput: **16.33 Mbps**

---

## Gap Experiment

### N = 1
$$
G = 135 - 57.03 = 77.97
$$
$$
\eta = 0.422
$$

### N = 2
$$
G = 67.5 - 25.59 = 41.91
$$
$$
\eta = 0.379
$$

### N = 3
$$
G = 45 - 16.33 = 28.67
$$
$$
\eta = 0.363
$$

---

## 왜 이론값과 실제값은 차이가 발생하는가?

이론적 상한과 실제 처리량 사이의 격차는 Wi-Fi의 구조적 특성에 의해 발생한다.

### 1. MAC 계층 경쟁 (CSMA/CA)
Wi-Fi는 CSMA/CA 기반으로 동작하므로 한 시점에 하나의 장치만 전송이 가능하다.  
사용자 수가 증가할수록 백오프 시간과 충돌 확률이 증가하여 효율이 감소한다.

### 2. 프로토콜 오버헤드
PHY 링크 속도는 실제 데이터만을 의미하지 않는다.  
MAC 헤더, TCP/IP 헤더, ACK 프레임, Inter-frame space 등이 포함되어 유효 데이터 전송 비율이 감소한다.

### 3. Half-duplex 특성
Wi-Fi는 반이중(half-duplex) 통신이므로 송수신을 동시에 수행할 수 없다.  
이는 유선(full-duplex) 환경 대비 구조적으로 낮은 효율을 초래한다.

### 4. TCP 혼잡 제어
Speedtest는 TCP 기반이므로 Slow Start, Congestion Window 조절 등의 영향으로 실제 전송률이 PHY 속도보다 낮게 나타난다.

---

## Conclusion

실험 결과, 실제 처리량은 PHY 기반 이론 상한 대비 약 36~42% 수준으로 측정되었다.  
또한 사용자 수가 증가할수록 효율은 0.422 → 0.363으로 감소하였다.

이는 다중 사용자 환경에서 채널 경쟁과 프로토콜 오버헤드가 성능 저하의 주요 원인임을 정량적으로 보여준다.
