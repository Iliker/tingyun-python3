# -*- coding: utf-8 -*-

"""提供上层接口计算分位数
"""

import logging
import copy

console = logging.getLogger(__name__)


class QuantileP2(object):
    """
    """
    def __init__(self, quartile_list):
        """分位数列表， 最多4个
        :param quartile_list: list
        """
        assert isinstance(quartile_list, list)
        assert len(quartile_list) > 0

        self.quartile_list = quartile_list
        self.quartile_list.sort()

        self.markers_y = [0.0 for _ in range(len(self.quartile_list) * 2 + 3)]
        self.markers_x = None
        self.count = 0
        self.p2_n = []

        self.init_marks()

    @property
    def markers(self):
        """
        :return:
        """
        if self.count < len(self.markers_y):
            result = [0 for _ in range(self.count)]
            markers = [0 for _ in range(len(self.markers_y))]
            pw_q_copy = copy.deepcopy(self.markers_y)
            pw_q_copy.sort()

            i = len(pw_q_copy) - self.count
            j = 0
            while i < len(pw_q_copy):
                result[j] = pw_q_copy[i]
                i += 1
                j += 1

            for i in range(len(pw_q_copy)):
                markers[i] = result[int(round((self.count - 1) * i * 1.0 / (len(pw_q_copy) - 1)))]

            return markers

        return self.markers_y

    def init_marks(self):
        """
        :return:
        """
        quartile_count = len(self.quartile_list)
        marker_count = quartile_count * 2 + 3

        self.markers_x = [0.0 for _ in range(marker_count)]
        self.p2_n = [0 for _ in range(len(self.markers_y))]

        for i in range(quartile_count):
            marker = self.quartile_list[i]
            self.markers_x[i * 2 + 1] = (marker + self.markers_x[i * 2]) / 2.0
            self.markers_x[i * 2 + 2] = marker

        self.markers_x[marker_count - 2] = (1 + self.quartile_list[quartile_count - 1]) / 2.0
        self.markers_x[marker_count - 1] = 1.0

        for i in range(marker_count):
            self.p2_n[i] = i

    def add(self, v):
        """
        :param v:
        :return:
        """
        if v is None:
            return

        obs_idx = self.count
        self.count += 1

        if obs_idx < len(self.markers_y):
            self.markers_y[obs_idx] = v

            if obs_idx == len(self.markers_y) - 1:
                self.markers_y.sort()
        else:
            k = self.binary_search(self.markers_y, v)
            if k < 0:
                k = -(k + 1)

            if 0 == k:
                self.markers_y[0] = v
                k = 1
            elif k == len(self.markers_y):
                k = len(self.markers_y) - 1
                self.markers_y[k] = v

            for i in range(k, len(self.p2_n)):
                self.p2_n[i] += 1

            for i in range(1, len(self.markers_y) - 1):
                n_ = self.markers_x[i] * obs_idx
                di = n_ - self.p2_n[i]

                if (di-1.0 >= 0.000001 and self.p2_n[i + 1] - self.p2_n[i] > 1) or \
                        (di+1.0 <= 0.000001 and self.p2_n[i - 1] - self.p2_n[i] < -1):
                    d = -1 if di < 0 else 1
                    qi_ = self.quad_pred(d, i)

                    if qi_ < self.markers_y[i - 1] or qi_ > self.markers_y[i + 1]:
                        qi_ = self.line_pred(d, i)

                    self.markers_y[i] = qi_
                    self.p2_n[i] += d

    def binary_search(self, data, v):
        """
        :param data:
        :param v:
        :return:
        """
        low, high = 0, len(data) - 1

        while low <= high:
            mid = (low + high) >> 1

            if data[mid] < v:
                low = mid + 1
            elif data[mid] > v:
                high = mid - 1
            else:
                if data[mid] == v:
                    return mid
                elif data[mid] < v:
                    low = mid + 1
                else:
                    high = mid - 1

        return -(low + 1)

    def quad_pred(self, d, i):
        """
        :param d:
        :param i:
        :return:
        """
        qi = self.markers_y[i]
        qip1 = self.markers_y[i + 1]
        qim1 = self.markers_y[i - 1]
        ni = self.p2_n[i]
        nip1 = self.p2_n[i + 1]
        nim1 = self.p2_n[i - 1]

        a = (ni - nim1 + d) * (qip1 - qi) / (nip1 - ni)
        b = (nip1 - ni - d) * (qi - qim1) / (ni - nim1)
        return qi + (d * (a + b)) / (nip1 - nim1)

    def line_pred(self, d, i):
        """
        :param d:
        :param i:
        :return:
        """
        qi = self.markers_y[i]
        qipd = self.markers_y[i + d]
        ni = self.p2_n[i]
        nipd = self.p2_n[i + d]

        return qi + d * (qipd - qi) / (nipd - ni)
